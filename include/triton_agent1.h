/*
 * SPDX-License-Identifier: MPL-2.0
 * Copyright (c) 2026 the Trust (see GOVERNANCE.md)
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 * Network administration authority is governed separately; see GOVERNANCE.md.
 */

/* ================================================================
 * TRITON AGENT 1
 * PHASE 1 — CORE COMPILER INFRASTRUCTURE
 *
 * Self-contained C11 implementation.
 * No external dependencies.
 *
 * This phase establishes the executable compiler foundation:
 * source -> lexer -> tokens -> AST -> semantic symbols -> IR
 *
 * Language frontends are deliberately separated so that documented
 * language syntax can be added without contaminating another frontend.
 * ================================================================ */

#ifndef TRITON_AGENT1_H
#define TRITON_AGENT1_H

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <errno.h>
#include <math.h>

/* ================================================================
 * MEMORY
 * ================================================================ */

static inline void *ta_malloc(size_t n)
{
    void *p = malloc(n ? n : 1);
    if (!p) {
        fprintf(stderr, "fatal: allocation failure\n");
        exit(EXIT_FAILURE);
    }
    return p;
}

static inline void *ta_calloc(size_t n, size_t s)
{
    void *p = calloc(n ? n : 1, s ? s : 1);
    if (!p) {
        fprintf(stderr, "fatal: allocation failure\n");
        exit(EXIT_FAILURE);
    }
    return p;
}

static inline void *ta_realloc(void *p, size_t n)
{
    void *q = realloc(p, n ? n : 1);
    if (!q) {
        fprintf(stderr, "fatal: allocation failure\n");
        exit(EXIT_FAILURE);
    }
    return q;
}

static inline char *ta_strdup(const char *s)
{
    size_t n = strlen(s);
    char *p = ta_malloc(n + 1);
    memcpy(p, s, n + 1);
    return p;
}

/* ================================================================
 * SOURCE LOCATION
 * ================================================================ */

typedef struct {
    uint32_t line;
    uint32_t column;
    uint32_t offset;
} TA_Location;

/* ================================================================
 * DIAGNOSTICS
 * ================================================================ */

typedef enum {
    TA_DIAG_NOTE,
    TA_DIAG_WARNING,
    TA_DIAG_ERROR,
    TA_DIAG_FATAL
} TA_DiagnosticKind;

typedef struct {
    TA_DiagnosticKind kind;
    TA_Location location;
    char *message;
} TA_Diagnostic;

typedef struct {
    TA_Diagnostic *items;
    size_t count;
    size_t capacity;
    size_t errors;
} TA_Diagnostics;

static inline void ta_diag_init(TA_Diagnostics *d)
{
    memset(d, 0, sizeof(*d));
}

static inline void ta_diag_push(
    TA_Diagnostics *d,
    TA_DiagnosticKind kind,
    TA_Location loc,
    const char *message)
{
    if (d->count == d->capacity) {
        size_t nc = d->capacity ? d->capacity * 2 : 16;
        d->items = ta_realloc(d->items, nc * sizeof(*d->items));
        d->capacity = nc;
    }

    TA_Diagnostic *x = &d->items[d->count++];
    x->kind = kind;
    x->location = loc;
    x->message = ta_strdup(message);

    if (kind == TA_DIAG_ERROR || kind == TA_DIAG_FATAL)
        d->errors++;
}

static inline void ta_diag_free(TA_Diagnostics *d)
{
    for (size_t i = 0; i < d->count; ++i)
        free(d->items[i].message);

    free(d->items);
    memset(d, 0, sizeof(*d));
}

/* ================================================================
 * LANGUAGE IDENTIFIER
 * ================================================================ */

typedef enum {
    TA_LANG_JOVIAL,
    TA_LANG_CMS2,
    TA_LANG_TACPOL
} TA_Language;

/* ================================================================
 * TOKEN MODEL
 * ================================================================ */

typedef enum {
    TOK_EOF = 0,

    TOK_IDENTIFIER,
    TOK_INTEGER,
    TOK_REAL,
    TOK_STRING,

    TOK_PLUS,
    TOK_MINUS,
    TOK_STAR,
    TOK_SLASH,

    TOK_ASSIGN,
    TOK_EQUAL,
    TOK_NOT_EQUAL,
    TOK_LESS,
    TOK_LESS_EQUAL,
    TOK_GREATER,
    TOK_GREATER_EQUAL,

    TOK_LPAREN,
    TOK_RPAREN,
    TOK_LBRACKET,
    TOK_RBRACKET,
    TOK_LBRACE,
    TOK_RBRACE,

    TOK_COMMA,
    TOK_COLON,
    TOK_SEMICOLON,
    TOK_DOT,

    TOK_UNKNOWN
} TA_TokenKind;

typedef struct {
    TA_TokenKind kind;
    TA_Location location;

    union {
        char *text;
        int64_t integer;
        double real;
    } value;
} TA_Token;

/* ================================================================
 * TOKEN VECTOR
 * ================================================================ */

typedef struct {
    TA_Token *items;
    size_t count;
    size_t capacity;
} TA_TokenVector;

static inline void token_vector_push(TA_TokenVector *v, TA_Token t)
{
    if (v->count == v->capacity) {
        size_t nc = v->capacity ? v->capacity * 2 : 128;
        v->items = ta_realloc(v->items, nc * sizeof(*v->items));
        v->capacity = nc;
    }

    v->items[v->count++] = t;
}

static inline void token_free(TA_Token *t)
{
    if (t->kind == TOK_IDENTIFIER ||
        t->kind == TOK_STRING) {
        free(t->value.text);
        t->value.text = NULL;
    }
}

static inline void token_vector_free(TA_TokenVector *v)
{
    for (size_t i = 0; i < v->count; ++i)
        token_free(&v->items[i]);

    free(v->items);
    memset(v, 0, sizeof(*v));
}

/* ================================================================
 * LEXER
 * ================================================================ */

typedef struct {
    const char *source;
    size_t length;
    size_t position;

    TA_Location location;

    TA_Diagnostics *diagnostics;
} TA_Lexer;

static inline bool lexer_at_end(const TA_Lexer *l)
{
    return l->position >= l->length;
}

static inline char lexer_peek(const TA_Lexer *l)
{
    if (lexer_at_end(l))
        return '\0';

    return l->source[l->position];
}

static inline char lexer_peek_next(const TA_Lexer *l)
{
    if (l->position + 1 >= l->length)
        return '\0';

    return l->source[l->position + 1];
}

static inline char lexer_advance(TA_Lexer *l)
{
    if (lexer_at_end(l))
        return '\0';

    char c = l->source[l->position++];

    if (c == '\n') {
        l->location.line++;
        l->location.column = 1;
    } else {
        l->location.column++;
    }

    l->location.offset++;

    return c;
}

static inline void lexer_init(
    TA_Lexer *l,
    const char *source,
    TA_Diagnostics *diagnostics)
{
    memset(l, 0, sizeof(*l));

    l->source = source;
    l->length = strlen(source);
    l->diagnostics = diagnostics;

    l->location.line = 1;
    l->location.column = 1;
}

static inline bool identifier_start(char c)
{
    return isalpha((unsigned char)c) || c == '_';
}

static inline bool identifier_continue(char c)
{
    return isalnum((unsigned char)c) || c == '_';
}

static inline TA_Token make_simple(
    TA_TokenKind kind,
    TA_Location loc)
{
    TA_Token t;
    memset(&t, 0, sizeof(t));
    t.kind = kind;
    t.location = loc;
    return t;
}

static inline TA_Token lexer_identifier(TA_Lexer *l)
{
    TA_Location loc = l->location;
    size_t start = l->position;

    while (identifier_continue(lexer_peek(l)))
        lexer_advance(l);

    size_t n = l->position - start;

    TA_Token t = make_simple(TOK_IDENTIFIER, loc);

    t.value.text = ta_malloc(n + 1);
    memcpy(t.value.text, l->source + start, n);
    t.value.text[n] = '\0';

    return t;
}

static inline TA_Token lexer_number(TA_Lexer *l)
{
    TA_Location loc = l->location;
    size_t start = l->position;

    while (isdigit((unsigned char)lexer_peek(l)))
        lexer_advance(l);

    bool real = false;

    if (lexer_peek(l) == '.' &&
        isdigit((unsigned char)lexer_peek_next(l))) {

        real = true;
        lexer_advance(l);

        while (isdigit((unsigned char)lexer_peek(l)))
            lexer_advance(l);
    }

    size_t n = l->position - start;

    char *text = ta_malloc(n + 1);
    memcpy(text, l->source + start, n);
    text[n] = '\0';

    TA_Token t = make_simple(
        real ? TOK_REAL : TOK_INTEGER,
        loc);

    errno = 0;
    if (real)
        t.value.real = strtod(text, NULL);
    else
        t.value.integer = strtoll(text, NULL, 10);

    if (errno == ERANGE || (real && !isfinite(t.value.real)))
        ta_diag_push(l->diagnostics, TA_DIAG_ERROR, loc, "numeric literal out of range");
    free(text);

    return t;
}

static inline TA_Token lexer_string(TA_Lexer *l)
{
    TA_Location loc = l->location;

    lexer_advance(l);

    size_t capacity = 32;
    size_t count = 0;

    char *buffer = ta_malloc(capacity);

    while (!lexer_at_end(l) && lexer_peek(l) != '"') {
        char c = lexer_advance(l);

        if (c == '\\' && !lexer_at_end(l)) {
            char e = lexer_advance(l);

            switch (e) {
            case 'n': c = '\n'; break;
            case 'r': c = '\r'; break;
            case 't': c = '\t'; break;
            case '\\': c = '\\'; break;
            case '"': c = '"'; break;
            default: c = e; break;
            }
        }

        if (count + 1 >= capacity) {
            capacity *= 2;
            buffer = ta_realloc(buffer, capacity);
        }

        buffer[count++] = c;
    }

    if (lexer_at_end(l)) {
        ta_diag_push(
            l->diagnostics,
            TA_DIAG_ERROR,
            loc,
            "unterminated string literal");
    } else {
        lexer_advance(l);
    }

    buffer[count] = '\0';

    TA_Token t = make_simple(TOK_STRING, loc);
    t.value.text = buffer;

    return t;
}

static inline TA_Token lexer_next(TA_Lexer *l)
{
    while (!lexer_at_end(l)) {
        char c = lexer_peek(l);

        if (isspace((unsigned char)c)) {
            lexer_advance(l);
            continue;
        }

        /*
         * Generic source comment handling.
         * Individual language frontends may impose stricter
         * comment rules before invoking this lexer.
         */
        if (c == '/' && lexer_peek_next(l) == '/') {
            while (!lexer_at_end(l) &&
                   lexer_peek(l) != '\n')
                lexer_advance(l);

            continue;
        }

        if (identifier_start(c))
            return lexer_identifier(l);

        if (isdigit((unsigned char)c))
            return lexer_number(l);

        TA_Location loc = l->location;

        switch (c) {
        case '"':
            return lexer_string(l);

        case '+':
            lexer_advance(l);
            return make_simple(TOK_PLUS, loc);

        case '-':
            lexer_advance(l);
            return make_simple(TOK_MINUS, loc);

        case '*':
            lexer_advance(l);
            return make_simple(TOK_STAR, loc);

        case '/':
            lexer_advance(l);
            return make_simple(TOK_SLASH, loc);

        case '(':
            lexer_advance(l);
            return make_simple(TOK_LPAREN, loc);

        case ')':
            lexer_advance(l);
            return make_simple(TOK_RPAREN, loc);

        case '[':
            lexer_advance(l);
            return make_simple(TOK_LBRACKET, loc);

        case ']':
            lexer_advance(l);
            return make_simple(TOK_RBRACKET, loc);

        case '{':
            lexer_advance(l);
            return make_simple(TOK_LBRACE, loc);

        case '}':
            lexer_advance(l);
            return make_simple(TOK_RBRACE, loc);

        case ',':
            lexer_advance(l);
            return make_simple(TOK_COMMA, loc);

        case ':':
            lexer_advance(l);

            if (lexer_peek(l) == '=') {
                lexer_advance(l);
                return make_simple(TOK_ASSIGN, loc);
            }

            return make_simple(TOK_COLON, loc);

        case ';':
            lexer_advance(l);
            return make_simple(TOK_SEMICOLON, loc);

        case '.':
            lexer_advance(l);
            return make_simple(TOK_DOT, loc);

        case '=':
            lexer_advance(l);
            return make_simple(TOK_EQUAL, loc);

        case '!':
            lexer_advance(l);

            if (lexer_peek(l) == '=') {
                lexer_advance(l);
                return make_simple(TOK_NOT_EQUAL, loc);
            }

            break;

        case '<':
            lexer_advance(l);

            if (lexer_peek(l) == '=') {
                lexer_advance(l);
                return make_simple(TOK_LESS_EQUAL, loc);
            }

            return make_simple(TOK_LESS, loc);

        case '>':
            lexer_advance(l);

            if (lexer_peek(l) == '=') {
                lexer_advance(l);
                return make_simple(TOK_GREATER_EQUAL, loc);
            }

            return make_simple(TOK_GREATER, loc);

        default:
            break;
        }

        lexer_advance(l);

        char message[96];
        snprintf(
            message,
            sizeof(message),
            "unrecognized character 0x%02X",
            (unsigned)(unsigned char)c);

        ta_diag_push(
            l->diagnostics,
            TA_DIAG_ERROR,
            loc,
            message);

        return make_simple(TOK_UNKNOWN, loc);
    }

    return make_simple(TOK_EOF, l->location);
}

static inline void lexer_all(
    TA_Lexer *lexer,
    TA_TokenVector *tokens)
{
    memset(tokens, 0, sizeof(*tokens));

    for (;;) {
        TA_Token t = lexer_next(lexer);
        token_vector_push(tokens, t);

        if (t.kind == TOK_EOF)
            break;
    }
}

/* ================================================================
 * AST
 * ================================================================ */

typedef enum {
    AST_PROGRAM,
    AST_BLOCK,
    AST_DECLARATION,
    AST_PARAMETER,
    AST_ASSIGNMENT,
    AST_CALL,
    AST_RETURN,
    AST_IF,
    AST_WHILE,
    AST_FOR,
    AST_BINARY,
    AST_UNARY,
    AST_INTEGER,
    AST_REAL,
    AST_STRING,
    AST_IDENTIFIER
} TA_ASTKind;

typedef struct TA_AST TA_AST;

typedef struct {
    TA_AST **items;
    size_t count;
    size_t capacity;
} TA_ASTVector;

static inline void ast_vector_push(TA_ASTVector *v, TA_AST *node)
{
    if (v->count == v->capacity) {
        size_t nc = v->capacity ? v->capacity * 2 : 16;
        v->items = ta_realloc(v->items, nc * sizeof(*v->items));
        v->capacity = nc;
    }

    v->items[v->count++] = node;
}

struct TA_AST {
    TA_ASTKind kind;
    TA_Location location;

    union {
        struct {
            char *name;
        } identifier;

        struct {
            int64_t value;
        } integer;

        struct {
            double value;
        } real;

        struct {
            char *value;
        } string;

        struct {
            TA_AST *left;
            TA_AST *right;
            TA_TokenKind operator_kind;
        } binary;

        struct {
            TA_TokenKind operator_kind;
            TA_AST *operand;
        } unary;

        struct {
            char *name;
            TA_ASTVector arguments;
        } call;

        struct {
            char *name;
            TA_AST *value;
        } assignment;

        struct {
            char *name;
            char *type_name;
        } declaration;

        struct {
            TA_AST *condition;
            TA_AST *then_branch;
            TA_AST *else_branch;
        } conditional;

        struct {
            TA_AST *condition;
            TA_AST *body;
        } loop;

        struct {
            TA_ASTVector statements;
        } block;

        struct {
            TA_ASTVector declarations;
            TA_AST *body;
        } program;
    } as;
};

static inline TA_AST *ast_new(TA_ASTKind kind, TA_Location loc)
{
    TA_AST *n = ta_calloc(1, sizeof(*n));
    n->kind = kind;
    n->location = loc;
    return n;
}

static inline TA_AST *ast_identifier(
    const char *name,
    TA_Location loc)
{
    TA_AST *n = ast_new(AST_IDENTIFIER, loc);
    n->as.identifier.name = ta_strdup(name);
    return n;
}

static inline TA_AST *ast_integer(
    int64_t value,
    TA_Location loc)
{
    TA_AST *n = ast_new(AST_INTEGER, loc);
    n->as.integer.value = value;
    return n;
}

static inline TA_AST *ast_real(
    double value,
    TA_Location loc)
{
    TA_AST *n = ast_new(AST_REAL, loc);
    n->as.real.value = value;
    return n;
}

static inline TA_AST *ast_string(
    const char *value,
    TA_Location loc)
{
    TA_AST *n = ast_new(AST_STRING, loc);
    n->as.string.value = ta_strdup(value);
    return n;
}

static inline void ast_free(TA_AST *n)
{
    if (!n)
        return;

    switch (n->kind) {

    case AST_IDENTIFIER:
        free(n->as.identifier.name);
        break;

    case AST_STRING:
        free(n->as.string.value);
        break;

    case AST_BINARY:
        ast_free(n->as.binary.left);
        ast_free(n->as.binary.right);
        break;

    case AST_UNARY:
        ast_free(n->as.unary.operand);
        break;

    case AST_ASSIGNMENT:
        free(n->as.assignment.name);
        ast_free(n->as.assignment.value);
        break;

    case AST_DECLARATION:
        free(n->as.declaration.name);
        free(n->as.declaration.type_name);
        break;

    case AST_CALL:
        free(n->as.call.name);

        for (size_t i = 0;
             i < n->as.call.arguments.count;
             ++i)
            ast_free(n->as.call.arguments.items[i]);

        free(n->as.call.arguments.items);
        break;

    case AST_BLOCK:
        for (size_t i = 0;
             i < n->as.block.statements.count;
             ++i)
            ast_free(n->as.block.statements.items[i]);

        free(n->as.block.statements.items);
        break;

    case AST_PROGRAM:
        for (size_t i = 0;
             i < n->as.program.declarations.count;
             ++i)
            ast_free(n->as.program.declarations.items[i]);

        free(n->as.program.declarations.items);

        ast_free(n->as.program.body);
        break;

    case AST_IF:
        ast_free(n->as.conditional.condition);
        ast_free(n->as.conditional.then_branch);
        ast_free(n->as.conditional.else_branch);
        break;

    case AST_WHILE:
        ast_free(n->as.loop.condition);
        ast_free(n->as.loop.body);
        break;

    default:
        break;
    }

    free(n);
}

/* ================================================================
 * TYPE SYSTEM
 * ================================================================ */

typedef enum {
    TA_TYPE_VOID,
    TA_TYPE_INTEGER,
    TA_TYPE_REAL,
    TA_TYPE_STRING,
    TA_TYPE_BOOLEAN,
    TA_TYPE_ADDRESS,
    TA_TYPE_ARRAY,
    TA_TYPE_RECORD,
    TA_TYPE_PROCEDURE,
    TA_TYPE_UNKNOWN
} TA_TypeKind;

typedef struct TA_Type TA_Type;

struct TA_Type {
    TA_TypeKind kind;

    size_t width;
    size_t alignment;

    TA_Type *element;
    size_t element_count;

    char *name;
};

static inline TA_Type *type_new(TA_TypeKind kind)
{
    TA_Type *t = ta_calloc(1, sizeof(*t));
    t->kind = kind;
    return t;
}

/* ================================================================
 * SYMBOL TABLE
 * ================================================================ */

typedef enum {
    TA_SYMBOL_VARIABLE,
    TA_SYMBOL_CONSTANT,
    TA_SYMBOL_TYPE,
    TA_SYMBOL_PROCEDURE,
    TA_SYMBOL_PARAMETER
} TA_SymbolKind;

typedef struct {
    char *name;
    TA_SymbolKind kind;
    TA_Type *type;
    TA_Location location;
} TA_Symbol;

typedef struct {
    TA_Symbol *items;
    size_t count;
    size_t capacity;
} TA_SymbolTable;

static inline void symbol_table_init(TA_SymbolTable *t)
{
    memset(t, 0, sizeof(*t));
}

static inline bool symbol_exists(
    const TA_SymbolTable *t,
    const char *name)
{
    for (size_t i = 0; i < t->count; ++i) {
        if (strcmp(t->items[i].name, name) == 0)
            return true;
    }

    return false;
}

static inline bool symbol_add(
    TA_SymbolTable *t,
    const char *name,
    TA_SymbolKind kind,
    TA_Type *type,
    TA_Location location)
{
    if (symbol_exists(t, name))
        return false;

    if (t->count == t->capacity) {
        size_t nc = t->capacity ? t->capacity * 2 : 32;

        t->items = ta_realloc(
            t->items,
            nc * sizeof(*t->items));

        t->capacity = nc;
    }

    TA_Symbol *s = &t->items[t->count++];

    s->name = ta_strdup(name);
    s->kind = kind;
    s->type = type;
    s->location = location;

    return true;
}

static inline TA_Symbol *symbol_find(
    TA_SymbolTable *t,
    const char *name)
{
    for (size_t i = 0; i < t->count; ++i) {
        if (strcmp(t->items[i].name, name) == 0)
            return &t->items[i];
    }

    return NULL;
}

static inline void symbol_table_free(TA_SymbolTable *t)
{
    for (size_t i = 0; i < t->count; ++i)
        free(t->items[i].name);

    free(t->items);

    memset(t, 0, sizeof(*t));
}

/* ================================================================
 * COMMON IR
 * ================================================================ */

typedef enum {
    IR_NOP,

    IR_CONST_I64,
    IR_CONST_F64,
    IR_CONST_STRING,

    IR_LOAD,
    IR_STORE,

    IR_ADD,
    IR_SUB,
    IR_MUL,
    IR_DIV,

    IR_NEG,

    IR_CMP_EQ,
    IR_CMP_NE,
    IR_CMP_LT,
    IR_CMP_LE,
    IR_CMP_GT,
    IR_CMP_GE,

    IR_JUMP,
    IR_BRANCH,

    IR_CALL,
    IR_RETURN,

    IR_LABEL,

    IR_ARRAY_INDEX,
    IR_FIELD_ACCESS
} TA_IROpcode;

typedef uint32_t TA_IRValue;
typedef uint32_t TA_IRBlock;

#define TA_IR_INVALID_VALUE UINT32_MAX
#define TA_IR_INVALID_BLOCK UINT32_MAX

typedef struct {
    TA_IROpcode opcode;

    TA_IRValue result;
    TA_IRValue a;
    TA_IRValue b;

    TA_IRBlock target;
    TA_IRBlock target_false;

    char *symbol;
    char *text;

    int64_t integer;
    double real;
} TA_IRInstruction;

typedef struct {
    TA_IRBlock id;
    TA_IRInstruction *instructions;
    size_t count;
    size_t capacity;
} TA_IRBasicBlock;

typedef struct {
    TA_IRBasicBlock *blocks;
    size_t block_count;
    size_t block_capacity;

    TA_IRValue next_value;

    TA_Type **value_types;
    size_t value_type_count;
    size_t value_type_capacity;
} TA_IRModule;

static inline void ir_init(TA_IRModule *m)
{
    memset(m, 0, sizeof(*m));
}

static inline TA_IRBlock ir_create_block(TA_IRModule *m)
{
    if (m->block_count == m->block_capacity) {
        size_t nc =
            m->block_capacity
                ? m->block_capacity * 2
                : 16;

        m->blocks = ta_realloc(
            m->blocks,
            nc * sizeof(*m->blocks));

        m->block_capacity = nc;
    }

    TA_IRBlock id = (TA_IRBlock)m->block_count;

    TA_IRBasicBlock *b = &m->blocks[m->block_count++];

    memset(b, 0, sizeof(*b));

    b->id = id;

    return id;
}

static inline TA_IRValue ir_new_value(
    TA_IRModule *m,
    TA_Type *type)
{
    TA_IRValue value = m->next_value++;

    if (value >= m->value_type_capacity) {
        size_t nc =
            m->value_type_capacity
                ? m->value_type_capacity * 2
                : 64;

        while (nc <= value)
            nc *= 2;

        m->value_types = ta_realloc(
            m->value_types,
            nc * sizeof(*m->value_types));

        for (size_t i = m->value_type_capacity;
             i < nc;
             ++i)
            m->value_types[i] = NULL;

        m->value_type_capacity = nc;
    }

    m->value_types[value] = type;

    if (value >= m->value_type_count)
        m->value_type_count = value + 1;

    return value;
}

static inline void ir_emit(
    TA_IRModule *m,
    TA_IRBlock block_id,
    TA_IRInstruction instruction)
{
    if (block_id >= m->block_count)
        return;

    TA_IRBasicBlock *b = &m->blocks[block_id];

    if (b->count == b->capacity) {
        size_t nc = b->capacity ? b->capacity * 2 : 32;

        b->instructions = ta_realloc(
            b->instructions,
            nc * sizeof(*b->instructions));

        b->capacity = nc;
    }

    b->instructions[b->count++] = instruction;
}

static inline void ir_free(TA_IRModule *m)
{
    for (size_t i = 0; i < m->block_count; ++i) free(m->blocks[i].instructions);
    for (size_t i = 0; i < m->value_type_count; ++i) {
        bool seen = false;
        for (size_t j = 0; j < i; ++j)
            if (m->value_types[j] == m->value_types[i]) seen = true;
        if (!seen) free(m->value_types[i]);
    }
    free(m->blocks); free(m->value_types); memset(m, 0, sizeof(*m));
}

/* ================================================================
 * IR BUILDER
 * ================================================================ */

typedef struct {
    TA_IRModule *module;
    TA_IRBlock current;
} TA_IRBuilder;

static inline TA_IRBuilder ir_builder(
    TA_IRModule *module)
{
    TA_IRBuilder b;

    b.module = module;
    b.current = ir_create_block(module);

    return b;
}

static inline TA_IRValue ir_const_i64(
    TA_IRBuilder *b,
    int64_t value)
{
    TA_Type *type = type_new(TA_TYPE_INTEGER);

    TA_IRValue result =
        ir_new_value(b->module, type);

    TA_IRInstruction i;
    memset(&i, 0, sizeof(i));

    i.opcode = IR_CONST_I64;
    i.result = result;
    i.integer = value;
    i.a = TA_IR_INVALID_VALUE;
    i.b = TA_IR_INVALID_VALUE;

    ir_emit(b->module, b->current, i);

    return result;
}

static inline TA_IRValue ir_binary(
    TA_IRBuilder *b,
    TA_IROpcode opcode,
    TA_IRValue left,
    TA_IRValue right)
{
    if (left >= b->module->next_value || right >= b->module->next_value)
        return TA_IR_INVALID_VALUE;
    TA_Type *type =
        b->module->value_types[left];

    TA_IRValue result =
        ir_new_value(b->module, type);

    TA_IRInstruction i;
    memset(&i, 0, sizeof(i));

    i.opcode = opcode;
    i.result = result;
    i.a = left;
    i.b = right;

    ir_emit(b->module, b->current, i);

    return result;
}

/* ================================================================
 * IR TEXT DUMP
 * ================================================================ */

static inline const char *ir_opcode_name(TA_IROpcode op)
{
    switch (op) {
    case IR_NOP: return "nop";
    case IR_CONST_I64: return "const.i64";
    case IR_CONST_F64: return "const.f64";
    case IR_CONST_STRING: return "const.string";
    case IR_LOAD: return "load";
    case IR_STORE: return "store";
    case IR_ADD: return "add";
    case IR_SUB: return "sub";
    case IR_MUL: return "mul";
    case IR_DIV: return "div";
    case IR_NEG: return "neg";
    case IR_CMP_EQ: return "cmp.eq";
    case IR_CMP_NE: return "cmp.ne";
    case IR_CMP_LT: return "cmp.lt";
    case IR_CMP_LE: return "cmp.le";
    case IR_CMP_GT: return "cmp.gt";
    case IR_CMP_GE: return "cmp.ge";
    case IR_JUMP: return "jump";
    case IR_BRANCH: return "branch";
    case IR_CALL: return "call";
    case IR_RETURN: return "return";
    case IR_LABEL: return "label";
    case IR_ARRAY_INDEX: return "array.index";
    case IR_FIELD_ACCESS: return "field.access";
    default: return "unknown";
    }
}

static inline void ir_dump(const TA_IRModule *m, FILE *out)
{
    for (size_t bi = 0; bi < m->block_count; ++bi) {
        const TA_IRBasicBlock *b = &m->blocks[bi];

        fprintf(out, "block_%u:\n", b->id);

        for (size_t i = 0; i < b->count; ++i) {
            const TA_IRInstruction *x =
                &b->instructions[i];

            fprintf(
                out,
                " ");

            if (x->result != TA_IR_INVALID_VALUE)
                fprintf(out, "%%v%u = ", x->result);

            fprintf(
                out,
                "%s",
                ir_opcode_name(x->opcode));

            switch (x->opcode) {
            case IR_CONST_I64:
                fprintf(out, " %lld",
                        (long long)x->integer);
                break;

            case IR_ADD:
            case IR_SUB:
            case IR_MUL:
            case IR_DIV:
            case IR_CMP_EQ:
            case IR_CMP_NE:
            case IR_CMP_LT:
            case IR_CMP_LE:
            case IR_CMP_GT:
            case IR_CMP_GE:
                fprintf(
                    out,
                    " %%v%u, %%v%u",
                    x->a,
                    x->b);
                break;

            default:
                break;
            }

            fputc('\n', out);
        }
    }
}

/* ================================================================
 * FRONTEND INTERFACE
 * ================================================================ */

typedef struct {
    TA_Language language;
    const char *name;

    /*
     * Frontends populate these functions independently.
     * No historical language is silently treated as another language.
     */
} TA_Frontend;

/* ================================================================
 * JOVIAL FRONTEND STATE
 * ================================================================ */

typedef struct {
    TA_Frontend frontend;

    TA_Diagnostics diagnostics;
    TA_TokenVector tokens;

    TA_SymbolTable symbols;
    TA_IRModule ir;
} TA_JovialCompiler;

static inline void jovial_compiler_init(TA_JovialCompiler *c)
{
    memset(c, 0, sizeof(*c));

    c->frontend.language = TA_LANG_JOVIAL;
    c->frontend.name = "JOVIAL";

    ta_diag_init(&c->diagnostics);
    symbol_table_init(&c->symbols);
    ir_init(&c->ir);
}

/* ================================================================
 * CMS-2 FRONTEND STATE
 * ================================================================ */

typedef struct {
    TA_Frontend frontend;

    TA_Diagnostics diagnostics;
    TA_TokenVector tokens;

    TA_SymbolTable symbols;
    TA_IRModule ir;
} TA_CMS2Compiler;

static inline void cms2_compiler_init(TA_CMS2Compiler *c)
{
    memset(c, 0, sizeof(*c));

    c->frontend.language = TA_LANG_CMS2;
    c->frontend.name = "CMS-2";

    ta_diag_init(&c->diagnostics);
    symbol_table_init(&c->symbols);
    ir_init(&c->ir);
}

/* ================================================================
 * TACPOL FRONTEND STATE
 * ================================================================ */

typedef struct {
    TA_Frontend frontend;

    TA_Diagnostics diagnostics;
    TA_TokenVector tokens;

    TA_SymbolTable symbols;
    TA_IRModule ir;
} TA_TACPOLCompiler;

static inline void tacpol_compiler_init(TA_TACPOLCompiler *c)
{
    memset(c, 0, sizeof(*c));

    c->frontend.language = TA_LANG_TACPOL;
    c->frontend.name = "TACPOL";

    ta_diag_init(&c->diagnostics);
    symbol_table_init(&c->symbols);
    ir_init(&c->ir);
}

/* ================================================================
 * GENERIC FRONTEND LEXICAL ENTRY
 * ================================================================ */

static inline bool compile_lexically(
    const char *source,
    TA_Diagnostics *diagnostics,
    TA_TokenVector *tokens)
{
    TA_Lexer lexer;

    lexer_init(
        &lexer,
        source,
        diagnostics);

    lexer_all(
        &lexer,
        tokens);

    return diagnostics->errors == 0;
}

/* ================================================================
 * COMMON EXPRESSION LOWERING
 * ================================================================ */

static inline TA_IRValue lower_expression(
    TA_IRBuilder *builder,
    TA_AST *node)
{
    if (!node)
        return TA_IR_INVALID_VALUE;

    switch (node->kind) {

    case AST_INTEGER:
        return ir_const_i64(
            builder,
            node->as.integer.value);

    case AST_BINARY: {
        TA_IRValue a =
            lower_expression(
                builder,
                node->as.binary.left);

        TA_IRValue b =
            lower_expression(
                builder,
                node->as.binary.right);

        switch (node->as.binary.operator_kind) {

        case TOK_PLUS:
            return ir_binary(
                builder,
                IR_ADD,
                a,
                b);

        case TOK_MINUS:
            return ir_binary(
                builder,
                IR_SUB,
                a,
                b);

        case TOK_STAR:
            return ir_binary(
                builder,
                IR_MUL,
                a,
                b);

        case TOK_SLASH:
            return ir_binary(
                builder,
                IR_DIV,
                a,
                b);

        default:
            return TA_IR_INVALID_VALUE;
        }
    }

    default:
        return TA_IR_INVALID_VALUE;
    }
}

/* ================================================================
 * TEST PROGRAM
 * ================================================================ */

#ifdef TRITON_AGENT1_TEST

int main(void)
{
    const char *source =
        "VALUE := 12 + 30 * 2;";

    TA_Diagnostics diagnostics;
    TA_TokenVector tokens;

    ta_diag_init(&diagnostics);

    if (!compile_lexically(
            source,
            &diagnostics,
            &tokens)) {

        for (size_t i = 0;
             i < diagnostics.count;
             ++i) {

            TA_Diagnostic *d =
                &diagnostics.items[i];

            fprintf(
                stderr,
                "%u:%u: %s\n",
                d->location.line,
                d->location.column,
                d->message);
        }

        token_vector_free(&tokens);
        ta_diag_free(&diagnostics);

        return EXIT_FAILURE;
    }

    for (size_t i = 0;
         i < tokens.count;
         ++i) {

        TA_Token *t = &tokens.items[i];

        printf(
            "token[%zu] kind=%d line=%u col=%u",
            i,
            (int)t->kind,
            t->location.line,
            t->location.column);

        if (t->kind == TOK_IDENTIFIER ||
            t->kind == TOK_STRING) {

            printf(
                " text=%s",
                t->value.text);
        }

        if (t->kind == TOK_INTEGER)
            printf(
                " value=%lld",
                (long long)t->value.integer);

        if (t->kind == TOK_REAL)
            printf(
                " value=%f",
                t->value.real);

        putchar('\n');
    }

    token_vector_free(&tokens);
    ta_diag_free(&diagnostics);

    return EXIT_SUCCESS;
}

#endif

#endif

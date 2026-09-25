/*
 * SPDX-License-Identifier: MPL-2.0
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 * Network administration authority is governed separately; see GOVERNANCE.md.
 */

/*
 * triton_agent1.c
 *
 * Executable compiler front-end core for:
 * JOVIAL
 * CMS-2
 * TACPOL
 *
 * This implementation deliberately establishes an executable,
 * mechanically testable core rather than inventing undocumented
 * historical syntax.
 *
 * Build:
 * cc -std=c11 -O2 -Wall -Wextra -pedantic triton_agent1.c -o triton-agent1
 *
 * Run:
 * ./triton-agent1 jovial source.jov
 * ./triton-agent1 cms2 source.cms
 * ./triton-agent1 tacpol source.tac
 * ./triton-agent1 test
 */

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include <ctype.h>
#include <errno.h>

/* ================================================================
 * MEMORY
 * ================================================================ */

#define MAX_SOURCE 1048576
#define MAX_TOKENS 65536
#define MAX_NODES 65536
#define MAX_SYMBOLS 16384
#define MAX_IR 65536
#define MAX_DIAGNOSTICS 1024

static void *xmalloc(size_t n)
{
    void *p = malloc(n ? n : 1);
    if (!p) {
        fprintf(stderr, "fatal: out of memory\n");
        exit(EXIT_FAILURE);
    }
    return p;
}

static void *xcalloc(size_t n, size_t s)
{
    void *p = calloc(n ? n : 1, s ? s : 1);
    if (!p) {
        fprintf(stderr, "fatal: out of memory\n");
        exit(EXIT_FAILURE);
    }
    return p;
}

static char *xstrdup(const char *s)
{
    size_t n = strlen(s);
    char *p = xmalloc(n + 1);
    memcpy(p, s, n + 1);
    return p;
}

/* ================================================================
 * DIALECT
 * ================================================================ */

typedef enum {
    DIALECT_JOVIAL,
    DIALECT_CMS2,
    DIALECT_TACPOL
} Dialect;

static const char *dialect_name(Dialect d)
{
    switch (d) {
        case DIALECT_JOVIAL: return "JOVIAL";
        case DIALECT_CMS2: return "CMS-2";
        case DIALECT_TACPOL: return "TACPOL";
    }
    return "UNKNOWN";
}

/* ================================================================
 * SOURCE LOCATION
 * ================================================================ */

typedef struct {
    unsigned line;
    unsigned column;
    size_t offset;
} SourceLoc;

/* ================================================================
 * TOKENS
 * ================================================================ */

typedef enum {
    TOK_EOF,
    TOK_IDENTIFIER,
    TOK_INTEGER,
    TOK_REAL,
    TOK_STRING,

    TOK_PLUS,
    TOK_MINUS,
    TOK_STAR,
    TOK_SLASH,
    TOK_ASSIGN,
    TOK_EQ,
    TOK_NE,
    TOK_LT,
    TOK_LE,
    TOK_GT,
    TOK_GE,

    TOK_LPAREN,
    TOK_RPAREN,
    TOK_LBRACKET,
    TOK_RBRACKET,
    TOK_COMMA,
    TOK_COLON,
    TOK_SEMICOLON,
    TOK_DOT,

    TOK_KW_BEGIN,
    TOK_KW_END,
    TOK_KW_IF,
    TOK_KW_THEN,
    TOK_KW_ELSE,
    TOK_KW_WHILE,
    TOK_KW_DO,
    TOK_KW_FOR,
    TOK_KW_RETURN,
    TOK_KW_CALL,
    TOK_KW_PROCEDURE,
    TOK_KW_FUNCTION,
    TOK_KW_ARRAY,
    TOK_KW_RECORD,
    TOK_KW_INTEGER,
    TOK_KW_REAL,
    TOK_KW_BOOLEAN,
    TOK_KW_STRING,
    TOK_KW_TRUE,
    TOK_KW_FALSE,
    TOK_KW_VAR,
    TOK_KW_CONST
} TokenKind;

typedef struct {
    TokenKind kind;
    char *text;
    SourceLoc loc;
    int64_t integer;
    double real;
} Token;

typedef struct {
    Token *items;
    size_t count;
    size_t capacity;
} TokenVec;

static void token_push(TokenVec *v, Token t)
{
    if (v->count == v->capacity) {
        v->capacity = v->capacity ? v->capacity * 2 : 256;
        v->items = realloc(v->items, v->capacity * sizeof(*v->items));
        if (!v->items) {
            fprintf(stderr, "fatal: token allocation failed\n");
            exit(EXIT_FAILURE);
        }
    }
    v->items[v->count++] = t;
}

static bool strieq(const char *a, const char *b)
{
    while (*a && *b) {
        if (toupper((unsigned char)*a) != toupper((unsigned char)*b))
            return false;
        ++a;
        ++b;
    }
    return *a == '\0' && *b == '\0';
}

static TokenKind keyword_kind(const char *s)
{
    if (strieq(s, "BEGIN")) return TOK_KW_BEGIN;
    if (strieq(s, "END")) return TOK_KW_END;
    if (strieq(s, "IF")) return TOK_KW_IF;
    if (strieq(s, "THEN")) return TOK_KW_THEN;
    if (strieq(s, "ELSE")) return TOK_KW_ELSE;
    if (strieq(s, "WHILE")) return TOK_KW_WHILE;
    if (strieq(s, "DO")) return TOK_KW_DO;
    if (strieq(s, "FOR")) return TOK_KW_FOR;
    if (strieq(s, "RETURN")) return TOK_KW_RETURN;
    if (strieq(s, "CALL")) return TOK_KW_CALL;
    if (strieq(s, "PROCEDURE")) return TOK_KW_PROCEDURE;
    if (strieq(s, "FUNCTION")) return TOK_KW_FUNCTION;
    if (strieq(s, "ARRAY")) return TOK_KW_ARRAY;
    if (strieq(s, "RECORD")) return TOK_KW_RECORD;
    if (strieq(s, "INTEGER")) return TOK_KW_INTEGER;
    if (strieq(s, "REAL")) return TOK_KW_REAL;
    if (strieq(s, "BOOLEAN")) return TOK_KW_BOOLEAN;
    if (strieq(s, "STRING")) return TOK_KW_STRING;
    if (strieq(s, "TRUE")) return TOK_KW_TRUE;
    if (strieq(s, "FALSE")) return TOK_KW_FALSE;
    if (strieq(s, "VAR")) return TOK_KW_VAR;
    if (strieq(s, "CONST")) return TOK_KW_CONST;
    return TOK_IDENTIFIER;
}

typedef struct {
    const char *source;
    size_t length;
    size_t pos;
    unsigned line;
    unsigned column;
    Dialect dialect;
    TokenVec tokens;
} Lexer;

static char lexer_peek(const Lexer *l)
{
    if (l->pos >= l->length)
        return '\0';
    return l->source[l->pos];
}

static char lexer_peek2(const Lexer *l)
{
    if (l->pos + 1 >= l->length)
        return '\0';
    return l->source[l->pos + 1];
}

static char lexer_advance(Lexer *l)
{
    char c = lexer_peek(l);

    if (c == '\0')
        return c;

    l->pos++;

    if (c == '\n') {
        l->line++;
        l->column = 1;
    } else {
        l->column++;
    }

    return c;
}

static void lexer_skip_space(Lexer *l)
{
    for (;;) {
        char c = lexer_peek(l);

        while (isspace((unsigned char)c)) {
            lexer_advance(l);
            c = lexer_peek(l);
        }

        /*
         * C-style comments are accepted by the implementation core.
         * This is intentionally independent of historical dialect
         * claims.
         */
        if (c == '/' && lexer_peek2(l) == '*') {
            lexer_advance(l);
            lexer_advance(l);

            while (lexer_peek(l) &&

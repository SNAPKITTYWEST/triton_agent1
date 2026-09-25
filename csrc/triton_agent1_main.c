/*
 * SPDX-License-Identifier: MPL-2.0
 * Copyright (c) 2026 the Trust (see GOVERNANCE.md)
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 * Network administration authority is governed separately; see GOVERNANCE.md.
 */

/* ================================================================
 * triton_agent1_main.c
 *
 * Executable driver.
 * ================================================================ */

#include "triton_agent1.h"

static const char *read_file(const char *path)
{
    FILE *f = fopen(path, "rb");

    if (!f) {
        fprintf(stderr, "cannot open %s\n", path);
        return NULL;
    }

    if (fseek(f, 0, SEEK_END) != 0) {
        fclose(f);
        return NULL;
    }

    long size = ftell(f);

    if (size < 0 || size > 1048576) {
        fprintf(stderr, "source size must be at most 1 MiB\n");
        fclose(f);
        return NULL;
    }

    rewind(f);

    char *buffer = ta_malloc((size_t)size + 1);

    size_t n = fread(
        buffer,
        1,
        (size_t)size,
        f);

    if (n != (size_t)size || ferror(f) || memchr(buffer, '\0', n)) {
        fprintf(stderr, "cannot read source or source contains NUL bytes\n");
        fclose(f); free(buffer); return NULL;
    }
    fclose(f);

    buffer[n] = '\0';

    return buffer;
}

static int compile_file(
    TA_Language language,
    const char *path)
{
    const char *source = read_file(path);

    if (!source)
        return EXIT_FAILURE;

    TA_Diagnostics diagnostics;
    TA_TokenVector tokens;

    ta_diag_init(&diagnostics);

    TA_Lexer lexer;

    lexer_init(
        &lexer,
        source,
        &diagnostics);

    lexer_all(
        &lexer,
        &tokens);

    for (size_t i = 0;
         i < diagnostics.count;
         ++i) {

        const TA_Diagnostic *d =
            &diagnostics.items[i];

        fprintf(
            stderr,
            "%s:%u:%u: %s\n",
            path,
            d->location.line,
            d->location.column,
            d->message);
    }

    if (diagnostics.errors != 0) {
        token_vector_free(&tokens);
        ta_diag_free(&diagnostics);
        free((void *)source);
        return EXIT_FAILURE;
    }

    TA_IRModule module;
    ir_init(&module);

    TA_IRBuilder builder =
        ir_builder(&module);

    /*
     * Core pipeline validation.
     *
     * Language-specific parsing/lowering is deliberately kept
     * separate from this executable infrastructure.
     */
    TA_IRValue a =
        ir_const_i64(&builder, 12);

    TA_IRValue b =
        ir_const_i64(&builder, 30);

    TA_IRValue c =
        ir_binary(
            &builder,
            IR_ADD,
            a,
            b);

    (void)c;

    printf(
        "TRITON AGENT 1 - lexical validation + fixed IR demonstration\n"
        "language=%d\n"
        "source=%s\n\n",
        (int)language,
        path);

    ir_dump(
        &module,
        stdout);

    ir_free(&module);
    token_vector_free(&tokens);
    ta_diag_free(&diagnostics);
    free((void *)source);

    return EXIT_SUCCESS;
}

int main(int argc, char **argv)
{
    if (argc == 2 && strcmp(argv[1], "--version") == 0) {
        puts("triton-agent1 0.2.0");
        return EXIT_SUCCESS;
    }
    if (argc != 3) {
        fprintf(
            stderr,
            "usage: triton-agent1 "
            "<jovial|cms2|tacpol> <source>\n");

        return EXIT_FAILURE;
    }

    TA_Language language;

    if (strcmp(argv[1], "jovial") == 0)
        language = TA_LANG_JOVIAL;
    else if (strcmp(argv[1], "cms2") == 0)
        language = TA_LANG_CMS2;
    else if (strcmp(argv[1], "tacpol") == 0)
        language = TA_LANG_TACPOL;
    else {
        fprintf(
            stderr,
            "unknown language: %s\n",
            argv[1]);

        return EXIT_FAILURE;
    }

    return compile_file(
        language,
        argv[2]);
}

/* SPDX-License-Identifier: Apache-2.0 */
#include "tree_sitter/parser.h"
#include <stdint.h>
#include <stdlib.h>
#include <wctype.h>

enum { BLOCK_COMMENT, RAW_STRING, INTERPOLATED_STRING };

void *tree_sitter_vela_external_scanner_create(void) { return NULL; }
void tree_sitter_vela_external_scanner_destroy(void *payload) { (void)payload; }
unsigned tree_sitter_vela_external_scanner_serialize(void *payload, char *buffer) {
    (void)payload;
    (void)buffer;
    return 0;
}
void tree_sitter_vela_external_scanner_deserialize(void *payload, const char *buffer, unsigned length) {
    (void)payload;
    (void)buffer;
    (void)length;
}

static void next(TSLexer *lexer) { lexer->advance(lexer, false); }

static bool comment(TSLexer *lexer) {
    if (lexer->lookahead != '/') return false;
    next(lexer);
    if (lexer->lookahead != '*') return false;
    next(lexer);
    unsigned depth = 1;
    while (!lexer->eof(lexer)) {
        int32_t current = lexer->lookahead;
        next(lexer);
        if (current == '/' && lexer->lookahead == '*') {
            if (++depth > 256) return false;
            next(lexer);
        } else if (current == '*' && lexer->lookahead == '/') {
            next(lexer);
            if (--depth == 0) return true;
        }
    }
    return false;
}

static bool raw(TSLexer *lexer) {
    unsigned quotes = 0;
    while (lexer->lookahead == '"') {
        ++quotes;
        next(lexer);
    }
    if (quotes < 3) return false;
    while (!lexer->eof(lexer)) {
        unsigned run = 0;
        while (lexer->lookahead == '"') {
            ++run;
            next(lexer);
        }
        if (run >= quotes) return run == quotes;
        if (!lexer->eof(lexer)) next(lexer);
    }
    return false;
}

static bool quoted(TSLexer *lexer, int32_t quote) {
    next(lexer);
    while (!lexer->eof(lexer)) {
        int32_t current = lexer->lookahead;
        next(lexer);
        if (current == quote) return true;
        if (current == '\\' && !lexer->eof(lexer)) next(lexer);
    }
    return false;
}

static bool interpolated(TSLexer *lexer) {
    if (lexer->lookahead != '$') return false;
    next(lexer);
    if (lexer->lookahead != '"') return false;
    next(lexer);
    unsigned braces = 0;
    while (!lexer->eof(lexer)) {
        int32_t current = lexer->lookahead;
        if (braces && current == '\'') {
            next(lexer);
            if (lexer->lookahead == '\\') {
                next(lexer);
                if (!lexer->eof(lexer)) next(lexer);
            } else if (!lexer->eof(lexer)) {
                next(lexer);
            }
            if (lexer->lookahead == '\'') next(lexer);
            continue;
        }
        if (braces && current == '"') {
            if (!quoted(lexer, current)) return false;
            continue;
        }
        next(lexer);
        if (current == '\\') {
            if (!lexer->eof(lexer)) next(lexer);
        } else if (current == '"' && !braces) {
            return true;
        } else if (current == '{') {
            if (!braces && lexer->lookahead == '{') next(lexer);
            else if (++braces > 256) return false;
        } else if (current == '}') {
            if (braces) --braces;
            else if (lexer->lookahead == '}') next(lexer);
            else return false;
        }
    }
    return false;
}

bool tree_sitter_vela_external_scanner_scan(void *payload, TSLexer *lexer, const bool *valid) {
    (void)payload;
    while (iswspace(lexer->lookahead)) lexer->advance(lexer, true);
    if (valid[BLOCK_COMMENT] && lexer->lookahead == '/') {
        lexer->result_symbol = BLOCK_COMMENT;
        return comment(lexer);
    }
    if (valid[RAW_STRING] && lexer->lookahead == '"') {
        lexer->result_symbol = RAW_STRING;
        return raw(lexer);
    }
    if (valid[INTERPOLATED_STRING] && lexer->lookahead == '$') {
        lexer->result_symbol = INTERPOLATED_STRING;
        return interpolated(lexer);
    }
    return false;
}

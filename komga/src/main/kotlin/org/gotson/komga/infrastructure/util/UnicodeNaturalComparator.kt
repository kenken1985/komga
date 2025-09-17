package org.gotson.komga.infrastructure.util

// Unicode-based natural comparator implementation (special symbols before numbers before letters)
object UnicodeNaturalComparator : Comparator<String> {
    
    override fun compare(sequence1: String, sequence2: String): Int {
        val len1 = sequence1.length
        val len2 = sequence2.length
        var idx1 = 0
        var idx2 = 0

        while (idx1 < len1 && idx2 < len2) {
            val c1 = sequence1[idx1++]
            val c2 = sequence2[idx2++]

            val isDigit1 = isDigit(c1)
            val isDigit2 = isDigit(c2)
            val isLetter1 = isLetter(c1)
            val isLetter2 = isLetter(c2)
            val isSpecialSymbol1 = isSpecialSymbol(c1)
            val isSpecialSymbol2 = isSpecialSymbol(c2)

            when {
                // Special symbols vs everything else - special symbols come first
                isSpecialSymbol1 && (isDigit2 || isLetter2) -> return -1
                (isDigit1 || isLetter1) && isSpecialSymbol2 -> return 1
                
                // Numbers vs letters - numbers come before letters
                isDigit1 && isLetter2 -> return -1
                isLetter1 && isDigit2 -> return 1
                
                // Same character type, compare directly
                else -> {
                    val c = compareChars(c1, c2)
                    if (c != 0) {
                        return c
                    }
                }
            }
        }

        return when {
            idx1 < len1 -> 1
            idx2 < len2 -> -1
            else -> 0
        }
    }
    
    private fun compareChars(c1: Char, c2: Char): Int {
        // Direct Unicode comparison
        return c1.code - c2.code
    }

    private fun isDigit(c: Char): Boolean {
        return c.isDigit()
    }

    private fun isLetter(c: Char): Boolean {
        return c.isLetter()
    }

    private fun isSpecialSymbol(c: Char): Boolean {
        // Define special symbols (non-alphanumeric Unicode characters)
        return when (c) {
            '_', '-', '.', ' ', ',', ';', ':', '!', '?', '(', ')', '[', ']', '{', '}',
            '<', '>', '=', '+', '*', '/', '\\', '|', '~', '`', '@', '#', '$', '%',
            '^', '&', '*', '-', '+', '=', '|', '\\', ' ', '\t', '\n', '\r' -> true
            else -> false
        }
    }
}
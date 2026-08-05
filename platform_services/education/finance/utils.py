def int_to_words_fr(n):
    units = ["", "un", "deux", "trois", "quatre", "cinq", "six", "sept", "huit", "neuf"]
    teens = ["dix", "onze", "douze", "treize", "quatorze", "quinze", "seize", "dix-sept", "dix-huit", "dix-neuf"]
    tens = ["", "dix", "vingt", "trente", "quarante", "cinquante", "soixante", "soixante-dix", "quatre-vingt", "quatre-vingt-dix"]

    if n == 0:
        return "zéro"

    def convert_less_than_1000(num):
        if num == 0:
            return ""
        elif num < 10:
            return units[num]
        elif num < 20:
            return teens[num - 10]
        elif num < 100:
            t, u = divmod(num, 10)
            if t == 7:
                if u == 1: return "soixante et onze"
                return "soixante-" + teens[u] if u else "soixante-dix"
            if t == 9:
                return "quatre-vingt-" + teens[u] if u else "quatre-vingt-dix"
            if u == 1 and t not in [8, 9]:
                return tens[t] + " et un"
            return tens[t] + ("-" + units[u] if u else ("s" if t == 8 else ""))
        else:
            h, rem = divmod(num, 100)
            prefix = "cent" if h == 1 else units[h] + " cent" + ("s" if not rem else "")
            return prefix + (" " + convert_less_than_1000(rem) if rem else "")

    words = ""
    millions, rem = divmod(int(n), 1000000)
    if millions:
        words += convert_less_than_1000(millions) + " million" + ("s" if millions > 1 else "") + " "
    thousands, rem = divmod(rem, 1000)
    if thousands:
        if thousands == 1:
            words += "mille "
        else:
            words += convert_less_than_1000(thousands) + " mille "
    if rem:
        words += convert_less_than_1000(rem)

    return words.strip()

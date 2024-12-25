def probe_converter_gold(weight, gold_standard):
    gold_sample858 = 585

    result = weight * gold_standard / gold_sample858
    return round(result, 2)


def probe_converter_silver(weight, gold_standard):
    silver_sample858 = 925

    result = weight * gold_standard / silver_sample858
    return round(result, 2)

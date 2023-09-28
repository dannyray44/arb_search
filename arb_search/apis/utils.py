from typing import Dict, Iterator

def fixed_count_bin_packer(data_table: Dict[int, list], max_weight: int = 250, items_per_bin: int = 40) -> Iterator[list]:
    """
    A bin packing algorithm that attempts to pack a fixed number of items with given weights into bins with a given weight limit to optimally reduce total bins used.

    Args:
        data_table Dict[key, List[val]]: Where key is an int representing the weight of each of the values in the list
        max_weight int: The maximum weight of each bin.
        items_per_bin int: The maximum number of items to pack into each bin.

    Returns:
        Iterator[List[val]]: An iterator of lists of values (bin) that are packed as optimally as possible.
    """

    ideal_gradient = max_weight / items_per_bin       #ideal item weight

    while data_table:
        current_bin = []
        current_bin_weight = 0

        for i in range(items_per_bin):
            weight_options = list(filter(lambda x: current_bin_weight+x <= max_weight, data_table.keys()))
            if not weight_options:
                break

            ideal_next_weight = (ideal_gradient * (i+1)) - current_bin_weight
            best_weight = min(weight_options, key = lambda x: abs(x-ideal_next_weight))

            current_bin.append(data_table[best_weight].pop())
            current_bin_weight += best_weight

            if data_table[best_weight] == []:
                data_table.pop(best_weight)

        yield current_bin
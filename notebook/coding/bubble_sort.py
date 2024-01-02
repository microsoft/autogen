# filename: bubble_sort.py
def bubble_sort(array):
    length = len(array)

    for i in range(length - 1):
        swapped = False
        for j in range(0, length - i - 1):
            if array[j] > array[j + 1]:
                array[j], array[j + 1] = array[j + 1], array[j]
                swapped = True
        if not swapped:
            break

    return array


array = [4, 1, 3, 5, 2]
print(bubble_sort(array))

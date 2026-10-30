CHANNEL_SIGNS = (1, 1, 1, 1)
OFFSETS = (0, 0, 0, 0)


def correlations(rows):
    return tuple(
        sign * (row[0] - row[1] - row[2] + row[3]) / sum(row) + offset
        for row, sign, offset in zip(rows, CHANNEL_SIGNS, OFFSETS)
    )

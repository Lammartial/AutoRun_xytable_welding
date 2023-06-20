import numpy as np

def calc_std_deviation(array: np.array, axis: int) -> np.array:
    """  
    
    The standard deviation is the square root of the average of the
    squared deviations from the mean, i.e., std = sqrt(mean(x)),
    where x = abs(a - a.mean())**2.

    Args:
        array (np.array): _description_
        axis (int): axis = 0 -> calculate vertically
    axis = 1 -> calculate horizontally

    Returns:
        np.array: _description_
    """
    return np.std(array, axis=int(axis))

# END OF FILE
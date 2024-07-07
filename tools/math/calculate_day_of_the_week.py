def calculate_day_of_the_week(total_days: int, starting_day: str):
    """
    Calculates the day of the week after a given number of days starting from a specified day.

    Args:
        total_days: The number of days to calculate.
        starting_day: The starting day of the week, should be one of 'Monday', 'Tuesday', 'Wednesday', etc.

    Returns:
        str: The day of the week after the specified number of days.
    """
    days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    start_index = days_of_week.index(starting_day)
    end_index = (start_index + total_days) % 7
    return days_of_week[end_index]

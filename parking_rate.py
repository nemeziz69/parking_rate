from datetime import datetime, timedelta
import calendar


REGISTRATION_NO = "SU 123 K"
TIME_IN = datetime(2023, 10, 6, 8, 16, 0, 57000)
TIME_OUT = datetime(2023, 10, 6, 8, 27, 0, 57000)


def get_duration(then: datetime, now: datetime):
    """
    Calculate parking fee that returns duration dict. Dict of duration (days, hours, minutes), "overall" key's indicate
    duration from then param until now param. While "first_day" key's indicate duration from then param until complete
    the whole day time (12am). The "remaining" key's indicate duration from start day of now param time until now
    param time. The "first day" and "remaining" key's exists if only then param and now param have changed date
    day-to-day. Also count days elapsed full 24 hours (weekday or weekend).

    :param then: Date and time then
    :param now: Date and time recent
    :return: duration_dict: Duration (days, hours, minutes) in dict
             elapsed_weekday_count: days elapsed in int
             elapsed_weekend_count: days elapsed in int
    """
    # Get overall duration
    duration_dict = {}
    duration_datetime = now - then
    days = duration_datetime.days
    hours = duration_datetime.seconds // 3600
    minutes = duration_datetime.seconds % 3600 // 60
    duration_dict["overall"] = {"days": days, "hours": hours, "minutes": minutes}

    # Get first day duration
    if not then.date() == now.date():
        # Get first day duration
        next_date = then + timedelta(days=1)
        next_day = datetime(next_date.year, next_date.month, next_date.day, 0, 1, 0, 00000)
        duration_first_day = next_day - then
        first_day_hours = duration_first_day.seconds // 3600
        first_day_minutes = duration_first_day.seconds % 3600 // 60
        duration_dict["first_day"] = {"hours": first_day_hours, "minutes": first_day_minutes}
        # Get remaining day duration
        duration_dict["remaining"] = {"hours": now.hour, "minutes": now.minute}

    # Get elapsed day
    elapsed_weekday_count = 0
    elapsed_weekend_count = 0
    for idx, i in enumerate(range(days)):
        day = calendar.day_name[(then + timedelta(days=i)).weekday()]
        is_weekend = True if day == "Saturday" or day == "Sunday" else False
        if idx != 0:
            if is_weekend:
                elapsed_weekend_count += 1
            else:
                elapsed_weekday_count += 1
    return duration_dict, elapsed_weekday_count, elapsed_weekend_count


def calculate_fee(duration_dict: dict, weekday_count: int, weekend_count: int, time_in_weekday: bool,
                  time_out_weekday: bool):
    """
    Calculate parking fee

    Method:
    1) Calculate fee for elapsed day (if any) by assign max charge * num of days. Max charge depend on rate type
    and elapsed day type weekday or weekend.
    2) If the duration involved with changed date (day-to-day or day-to-weekend), calculate fee for first day
    according to rules (first n hours, 15 minutes FOC, grace period, subsequent hours). Then, calculate remaining hours
    and minutes for checking out date follow rules (grace period, subsequent hours).
    3) Otherwise, calculate fee for first day according to rules (first n hours, 15 minutes FOC, grace period,
    subsequent hours).

    :param duration_dict: Dict of duration information (days, hours, minutes)
    :param weekday_count: Total full 24 hours elapsed on significant date for weekday in int
    :param weekend_count: Total full 24 hours elapsed on significant date for weekend in int
    :param time_in_weekday: Bool True if date time check-in was in weekday else False
    :param time_out_weekday: Bool True if date time check-out was in weekday else False
    :return: total_fee: Calculated total fee in float
    """
    # Unpack
    overall_duration_hours = duration_dict["overall"]["hours"]
    overall_duration_minutes = duration_dict["overall"]["minutes"]
    try:
        first_duration_hours = duration_dict["first_day"]["hours"]
        first_duration_minutes = duration_dict["first_day"]["minutes"]
        remaining_hours = duration_dict["remaining"]["hours"]
        remaining_minutes = duration_dict["remaining"]["minutes"]
    except KeyError:
        first_duration_hours = None
        first_duration_minutes = None
        remaining_hours = None
        remaining_minutes = None

    # Define rate
    first_n_hours = 3
    free_of_charge_minutes = 15
    grace_period_minutes = 5
    weekday_first_n_hours_rate = 3.0
    weekday_subsequent_hours = 1.5
    weekday_max_charge_per_day = 20.0
    weekend_first_n_hours_rate = 5.0
    weekend_subsequent_hours = 2.0
    weekend_max_charge_per_day = 40.0
    # Define rate based on day type weekday or weekend
    first_n_hours_rate = weekday_first_n_hours_rate if time_in_weekday else weekend_first_n_hours_rate
    first_day_subsequent_hours_rate = weekday_subsequent_hours if time_in_weekday else weekend_subsequent_hours
    first_day_max_rate = weekday_max_charge_per_day if time_in_weekday else weekend_max_charge_per_day
    remaining_subsequent_hours_rate = weekday_subsequent_hours if time_out_weekday else weekend_subsequent_hours
    remaining_max_rate = weekday_max_charge_per_day if time_out_weekday else weekend_max_charge_per_day

    # Calculate elapsed day rate
    if weekday_count != 0 or weekend_count != 0:
        elapsed_days_fee = (weekday_count * weekday_max_charge_per_day) + (weekend_count * weekend_max_charge_per_day)
    else:
        elapsed_days_fee = 0

    # Get which duration to use, if day-to-day involved, choose first day duration, otherwise, use overall duration
    if first_duration_hours is not None:
        hours_to_calculate = first_duration_hours
        minutes_to_calculate = first_duration_minutes
    else:
        hours_to_calculate = overall_duration_hours
        minutes_to_calculate = overall_duration_minutes

    # Calculate based on hour rate for start date
    if hours_to_calculate > first_n_hours:  # if more than N hours, calculate based on subsequent rate
        first_day_fee = first_n_hours_rate + (first_day_subsequent_hours_rate * (hours_to_calculate - first_n_hours))
    elif hours_to_calculate == first_n_hours:  # if exactly N hours, use N hours rate
        first_day_fee = first_n_hours_rate
    elif hours_to_calculate < first_n_hours:  # if less than N hours
        if hours_to_calculate < 1:  # if less than 1 hour, apply 15 minutes FOC
            if minutes_to_calculate > free_of_charge_minutes:
                first_day_fee = first_day_subsequent_hours_rate
            else:
                first_day_fee = 0.0
        else:
            first_day_fee = first_day_subsequent_hours_rate * hours_to_calculate
    else:
        first_day_fee = first_day_subsequent_hours_rate * hours_to_calculate

    # Calculate grace period if duration same or more than 1 hour
    if hours_to_calculate >= 1:
        if minutes_to_calculate > grace_period_minutes:
            first_day_fee += first_day_subsequent_hours_rate

    # Check if exceed max rate
    if first_day_fee > first_day_max_rate:
        first_day_fee = first_day_max_rate

    # Calculate remaining hours and minutes if day-to-day involved
    if remaining_hours is not None:
        remaining_hours_fee = remaining_hours * remaining_subsequent_hours_rate
        # Calculate grace period
        if remaining_hours >= 1:
            if remaining_minutes > grace_period_minutes:
                remaining_hours_fee += remaining_subsequent_hours_rate
        # Check if exceed max rate
        if remaining_hours_fee > remaining_max_rate:
            remaining_hours_fee = remaining_max_rate
    else:
        remaining_hours_fee = 0.0

    # Total rate
    total_fee = first_day_fee + elapsed_days_fee + remaining_hours_fee

    return total_fee


def get_parking_fee(time_in: datetime, time_out: datetime):
    """
    Pre-process parking fee information and get parking fee

    :param time_in: Date and time car check in
    :param time_out: Date and time car check out
    :return: duration_str: Duration from time in until time out in string
             total_fee: Calculated total fee in float
    """

    # Check validity, time out should be bigger than time in
    elapsed = time_out - time_in
    if elapsed.days < 0:
        raise "Time out date should not be smaller than time in"

    # Calculate duration
    duration_dict, weekday_count, weekend_count = get_duration(time_in, time_out)

    # Determine time in is weekday or weekend
    time_in_weekday = True if time_in.weekday() < 5 else False
    time_out_weekday = True if time_out.weekday() < 5 else False

    # Calculate fee
    total_fee = calculate_fee(duration_dict, weekday_count, weekend_count, time_in_weekday, time_out_weekday)

    # Construct duration in str
    overall_duration_days = duration_dict["overall"]["days"]
    overall_duration_hours = duration_dict["overall"]["hours"]
    overall_duration_minutes = duration_dict["overall"]["minutes"]
    total_hours = (overall_duration_days * 24) + overall_duration_hours
    if 1 <= total_hours < 24:
        duration_str = f"{overall_duration_hours} hours {overall_duration_minutes} minutes"
    elif total_hours < 1:
        duration_str = f"{overall_duration_minutes} minutes"
    else:
        duration_str = f"{total_hours} hours"

    return duration_str, total_fee


def main():
    # Get parking fee based on time in and time out
    time_duration, amount_to_paid = get_parking_fee(TIME_IN, TIME_OUT)

    # Output
    print(f"Reg No\t: {REGISTRATION_NO}\n"
          f"In\t: {TIME_IN}\n"
          f"Out\t: {TIME_OUT}\n"
          f"Duration\t: {time_duration}\n"
          f"Amount to paid\t: $ {amount_to_paid}\n"
          )


if __name__ == "__main__":
    main()

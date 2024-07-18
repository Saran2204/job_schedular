def parse_day_of_week(day_of_week):
    days = {
        '0': 'Sunday',
        '1': 'Monday',
        '2': 'Tuesday',
        '3': 'Wednesday',
        '4': 'Thursday',
        '5': 'Friday',
        '6': 'Saturday',
        '7': 'Sunday'
    }
    day_list = day_of_week.split(',')
    return [days.get(day, day) for day in day_list]

def extract_recurrence_interval(part):
    if '*/' in part:
        return int(part.split('*/')[1])
    return None
    
def parse_cron_expression(expression):
    parts = expression.split()
    if len(parts) != 5:
        raise ValueError("Cron expression must have 5 parts")
    
    parsed_expression = {
        'minute': parts[0],
        'hour': parts[1],
        'day_of_month': parts[2],
        'month': parts[3],
        'day_of_week': parse_day_of_week(parts[4]),
    }
    
    return parsed_expression
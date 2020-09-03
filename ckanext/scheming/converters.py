import datetime

def convert_from_extras_group(key, data, errors, context):
    '''Converts values from extras, tailored for groups.'''

    def remove_from_extras(data, key):
        for data_key in sorted(data):
            if data_key[0] != 'extras' or data_key[1] < key:
                continue
            if data_key[1] == key:
                del data[data_key]

            # Following block required for unflattening extras with
            # "gaps" created sometimes by `convert_from_extra`
            # validator :
            #
            #   {
            #     ('extras', 0, 'key'): 'x',
            #     ('extras', 2, 'key): 'y'
            #   }
            if data_key[1] > key:
                new_key = (data_key[0], data_key[1] - 1) + data_key[2:]
                data[new_key] = data.pop(data_key)

    for data_key, data_value in data.items():
        if (data_key[0] == 'extras'
            and 'key' in data_value
                and data_value['key'] == key[-1]):
            data[key] = data_value['value']
            break
    else:
        return
    remove_from_extras(data, data_key[1])


def convert_to_json_if_date(date, context):
    if isinstance(date, datetime.datetime):
        return date.date().isoformat()
    elif isinstance(date, datetime.date):
        return date.isoformat()
    else:
        return date

def convert_to_json_if_datetime(date, context):
    if isinstance(date, datetime.datetime):
        return date.isoformat()

    return date

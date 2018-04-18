# Based on https://stackoverflow.com/a/3041990
def query_yes_no(question, default='yes'):
    '''
    Ask a yes/no question via input() and return the user's answer.

    :param str question: Prompt given to the user.
    :param str default: The assumed answer if th user just hits **Enter**. It
        must be ``'yes'`` (the default if no default is given), ``'no'``, or
        ``None`` (meaning an answer is required from the user).
    :returns: ``True`` if we ended up with a 'yes' answer, otherwise
        ``False``.
    '''
    valid = {'yes': True, 'y': True, 'ye': True, 'no': False, 'n': False}
    if default is None:
        prompt = ' [y/n] '
    elif default == 'yes':
        prompt = ' [Y/n] '
    elif default == 'no':
        prompt = ' [y/N] '
    else:
        raise ValueError('invalid default answer: "%s"' % default)
    while True:
        print(question + prompt, end='')
        choice = input().lower()
        if default is not None and choice == '':
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            print('Please respond with "yes" or "no" (or "y" or "n").\n')

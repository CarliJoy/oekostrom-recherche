def info(msg: str, **kwargs: str) -> None:
    to_log = msg
    for key, value in kwargs.items():
        to_log = f'{to_log} {key}={value}'
    print(f"INFO: {to_log}")
class NoContentFound(Exception):
    """ Exception for if CAISO returns no content. """
    
    status_code = 400

    def __init__(self, message, status_code=None):
        super().__init__()
        self.message = message
        if status_code is not None:
            self.status_code = status_code

    def to_dict(self):
        rv = {}
        rv['message'] = self.message
        return rv
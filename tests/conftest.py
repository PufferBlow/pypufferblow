
class ValueStorage:
    """
    Value storage class for sharing constants across tests cases
    """
    def __init__(self):
        self.username : str = "user1"
        self.password : str = "12345678"
        self.new_username : str = "new_user1"
        self.new_password : str = "123456789"
        self.auth_token : str = None
        self.bad_formated_auth_token : str = "abcdwqwpdopok"

value_storage = ValueStorage()

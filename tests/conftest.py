
class ValueStorage:
    """
    Value storage class for sharing constants across tests cases
    """
    username                    :   str     =   "user1"
    password                    :   str     =   "12345678"
    new_username                :   str     =   "new_user1"
    new_password                :   str     =   "123456789"
    auth_token                  :   None
    bad_formated_auth_token     :   str     =   "abcdwqwpdopok"

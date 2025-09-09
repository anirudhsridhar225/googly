from firebase_admin import credentials, firestore, initialize_app, get_app


class DB:
    """
    Firestore database helper.

    Handles initialization of Firebase Admin SDK and
    returns a Firestore client. Ensures the app is only
    initialized once per process.
    """

    def __init__(self, path: str):
        """
        Initialize the DB helper.

        Args:
            path (str): Path to the Firebase service account JSON key file.
        """
        self.serviceKey = path
        self.db = None

    def db_init(self):
        """
        Initialize Firestore client.

        - If Firebase Admin is already initialized, reuse the existing app.
        - Otherwise, initialize with the provided service account key.

        Returns:
            google.cloud.firestore.Client: Firestore client instance.
        """
        try:
            get_app()
        except ValueError:
            cred = credentials.Certificate(self.serviceKey)
            initialize_app(cred)

        self.db = firestore.client()
        return self.db

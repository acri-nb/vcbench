# models.py
Defines the structure of the database tables using SQLAlchemy ORM.

# schemas.py
Defines the pydantic models that validate data for the API.

# crud.py
Contains CRUD (Create, Read, Update, Delete) operations that interact with the database.

# database.pyn
Sets up the database engine, session factory, and FastAPI dependency

# main.py
Sets up the FastAPI app, sets middleware to mount Dash and includes endpoint routers.
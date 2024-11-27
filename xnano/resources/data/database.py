from typing import Type, List, Union, Optional, Literal
from pydantic import BaseModel, Field

from ...lib import console, XNANOException
from ..completions.main import completion
from pathlib import Path


from ...types.completions.params import (
    CompletionChatModelsParam,
    CompletionInstructorModeParam,
)


class SQLResponse(BaseModel):
    sql_query: str = Field(..., description="The generated SQL query.")


class SQLQueryTemplate(BaseModel):
    """Model for SQL query templates with placeholders"""

    template: str = Field(..., description="SQL query template with placeholders")


class SQLBatchInsert(BaseModel):
    """Model for batch insert statements"""

    values: List[str] = Field(..., description="List of value tuples for batch insert")


class Database:
    def __init__(
        self,
        db_url: Literal[":memory:"] = ":memory:",
        model: Optional[Type[BaseModel]] = None,
        verbose: bool = False,
    ):
        """
        Initializes the Database client.

        Args:
            db_url (str): Database connection string.
            model (Optional[Type[BaseModel]]): Optional Pydantic model to use as schema.
            verbose (bool): Whether to print verbose messages.
        """
        if db_url == ":memory:":
            self.db_url = "sqlite:///:memory:"
        else:
            if not Path(db_url).is_absolute() and not db_url.startswith("./"):
                db_url = f"./{db_url}"
            self.db_url = db_url

        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        self.verbose = verbose
        self.engine = create_engine(self.db_url)
        self.Session = sessionmaker(bind=self.engine)
        self.model = model

        if self.verbose:
            console.message(f"Connected to database at {db_url}")

        if model:
            self.create_table(model)

    def create_table(self, model: Type[BaseModel]):
        """
        Creates a table based on the provided Pydantic model.

        Args:
            model (Type[BaseModel]): Pydantic model representing the schema.
        """
        from sqlalchemy import Table, Column, Integer, String, Float, Boolean, MetaData

        self.model = model
        metadata = MetaData()
        columns = []

        # Generate SQLAlchemy columns from Pydantic model fields
        for name, field in model.model_fields.items():
            if field.annotation == int:
                columns.append(Column(name, Integer))
            elif field.annotation == float:
                columns.append(Column(name, Float))
            elif field.annotation == bool:
                columns.append(Column(name, Boolean))
            elif field.annotation == str:
                columns.append(Column(name, String))
            else:
                # Default to String if type is unknown
                columns.append(Column(name, String))

        self.table = Table(model.__name__, metadata, *columns)

        # Ensure consistent error handling
        try:
            metadata.create_all(self.engine)
        except Exception as e:
            raise XNANOException(f"Failed to create table {model.__name__}: {e}") from e

        if self.verbose:
            console.message(
                f"Created table {model.__name__} with columns {', '.join([col.name for col in columns])}"
            )

    def add(
        self,
        instances: Union[BaseModel, List[BaseModel]],
        instructions: Optional[str] = None,
        model_name: CompletionChatModelsParam = "gpt-4o-mini",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        organization: Optional[str] = None,
        temperature: float = 0,
        mode: CompletionInstructorModeParam = "tool_call",
        max_completion_tokens: Optional[int] = None,
    ):
        """
        Adds instances to the database.

        Args:
            instances (Union[BaseModel, List[BaseModel]]): Instance or list of instances to add.
            instructions (Optional[str]): Additional instructions for the LLM.
            model_name (str): Model to use for LLM.
            api_key (Optional[str]): API key for LLM service.
            base_url (Optional[str]): Base URL for LLM service.
            organization (Optional[str]): Organization for LLM service.
            temperature (float): Temperature for LLM generation.
            mode (str): Mode for LLM generation.
            max_completion_tokens (Optional[int]): Max tokens for LLM completion.
        """
        if not isinstance(instances, list):
            instances = [instances]

        for instance in instances:
            # Generate SQL INSERT query using LLM
            sql_query = self._generate_sql_query(
                action="insert",
                instance=instance,
                instructions=instructions,
                model_name=model_name,
                api_key=api_key,
                base_url=base_url,
                organization=organization,
                temperature=temperature,
                mode=mode,
                max_completion_tokens=max_completion_tokens,
            )

            # Execute the query
            self._execute_sql(sql_query)

            if self.verbose:
                console.message(f"Added instance {instance} to the database.")

    def remove(
        self,
        condition: str,
        instructions: Optional[str] = None,
        model_name: CompletionChatModelsParam = "gpt-4o-mini",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        organization: Optional[str] = None,
        temperature: float = 0,
        mode: CompletionInstructorModeParam = "tool_call",
        max_completion_tokens: Optional[int] = None,
    ):
        """
        Removes instances from the database based on condition.

        Args:
            condition (str): Condition for deletion (e.g., "id = 1").
            instructions (Optional[str]): Additional instructions for the LLM.
            model_name (str): Model to use for LLM.
            api_key (Optional[str]): API key for LLM service.
            base_url (Optional[str]): Base URL for LLM service.
            organization (Optional[str]): Organization for LLM service.
            temperature (float): Temperature for LLM generation.
            mode (str): Mode for LLM generation.
            max_completion_tokens (Optional[int]): Max tokens for LLM completion.
        """
        # Generate SQL DELETE query using LLM
        sql_query = self._generate_sql_query(
            action="delete",
            condition=condition,
            instructions=instructions,
            model_name=model_name,
            api_key=api_key,
            base_url=base_url,
            organization=organization,
            temperature=temperature,
            mode=mode,
            max_completion_tokens=max_completion_tokens,
        )

        # Execute the query
        self._execute_sql(sql_query)

        if self.verbose:
            console.message(f"Removed records where {condition}.")

    def search(
        self,
        condition: str,
        instructions: Optional[str] = None,
        model_name: CompletionChatModelsParam = "gpt-4o-mini",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        organization: Optional[str] = None,
        temperature: float = 0,
        mode: CompletionInstructorModeParam = "tool_call",
        max_completion_tokens: Optional[int] = None,
    ) -> List[BaseModel]:
        """
        Searches the database based on condition.

        Args:
            condition (str): Condition for search (e.g., "age > 20").
            instructions (Optional[str]): Additional instructions for the LLM.
            model_name (str): Model to use for LLM.
            api_key (Optional[str]): API key for LLM service.
            base_url (Optional[str]): Base URL for LLM service.
            organization (Optional[str]): Organization for LLM service.
            temperature (float): Temperature for LLM generation.
            mode (str): Mode for LLM generation.
            max_completion_tokens: (Optional[int]): Max tokens for LLM completion.

        Returns:
            List[BaseModel]: List of instances matching the condition.
        """
        # Generate SQL SELECT query using LLM
        sql_query = self._generate_sql_query(
            action="select",
            condition=condition,
            instructions=instructions,
            model_name=model_name,
            api_key=api_key,
            base_url=base_url,
            organization=organization,
            temperature=temperature,
            mode=mode,
            max_completion_tokens=max_completion_tokens,
        )

        # Execute the query and fetch results
        results = self._execute_sql(sql_query, fetch=True)

        # Convert results to instances of the model
        instances = [self.model(**dict(row)) for row in results]

        if self.verbose:
            console.message(
                f"Found {len(instances)} records matching condition '{condition}'."
            )

        return instances

    def _generate_sql_query(
        self,
        action: str,
        instance: Optional[BaseModel] = None,
        condition: Optional[str] = None,
        instructions: Optional[str] = None,
        model_name: str = "gpt-4o-mini",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        organization: Optional[str] = None,
        temperature: float = 0,
        mode: str = "sql_generation",
        max_completion_tokens: Optional[int] = None,
    ) -> str:
        """Generates SQL query using templates and placeholders"""

        if action == "insert":
            # Get template first
            prompt = f"""Generate a SQL INSERT template for table '{{table_name}}' with placeholders.
            The columns are: {', '.join(self.table.columns.keys())}
            Use {{values}} as placeholder for the values."""

            if instructions:
                prompt += f"\n{instructions}"

            template_response = completion(
                messages=[{"role": "user", "content": prompt}],
                model=model_name,
                temperature=temperature,
                api_key=api_key,
                base_url=base_url,
                organization=organization,
                max_completion_tokens=max_completion_tokens,
                mode=mode,
                response_model=SQLQueryTemplate,
            )

            # Format template with actual values
            instance_data = instance.model_dump()
            values = f"({', '.join(repr(v) for v in instance_data.values())})"
            sql_query = template_response.template.format(
                table_name=self.table.name, values=values
            )

        elif action == "delete":
            prompt = f"""Generate a SQL DELETE template with {{condition}} placeholder.
            Table name will be {{table_name}}."""

            if instructions:
                prompt += f"\n{instructions}"

            template_response = completion(
                messages=[{"role": "user", "content": prompt}],
                model=model_name,
                temperature=temperature,
                api_key=api_key,
                base_url=base_url,
                organization=organization,
                max_completion_tokens=max_completion_tokens,
                mode=mode,
                response_model=SQLQueryTemplate,
            )

            sql_query = template_response.template.format(
                table_name=self.table.name, condition=condition
            )

        elif action == "select":
            prompt = f"""Generate a SQL SELECT template with {{condition}} placeholder.
            Table name will be {{table_name}}."""

            if instructions:
                prompt += f"\n{instructions}"

            template_response = completion(
                messages=[{"role": "user", "content": prompt}],
                model=model_name,
                temperature=temperature,
                api_key=api_key,
                base_url=base_url,
                organization=organization,
                max_completion_tokens=max_completion_tokens,
                mode=mode,
                response_model=SQLQueryTemplate,
            )

            sql_query = template_response.template.format(
                table_name=self.table.name, condition=condition
            )

        else:
            raise XNANOException(f"Unknown action '{action}' for SQL query generation.")

        if self.verbose:
            console.message(f"Generated SQL query: {sql_query}")

        return sql_query

    def _execute_sql(self, sql_query: str, fetch: bool = False):
        """
        Executes the given SQL query.

        Args:
            sql_query (str): SQL query to execute.
            fetch (bool): Whether to fetch and return results.

        Returns:
            If fetch is True, returns query results.
        """
        from sqlalchemy import text

        with self.engine.connect() as connection:
            result = connection.execute(text(sql_query))

            if fetch:
                return result.fetchall()

    def launch_sql_editor(self):
        """Launches a SQL editor in the browser"""
        from sqlalchemy.engine import URL

        try:
            from IPython.display import HTML
        except ImportError:
            raise XNANOException(
                "IPython is not installed. Please install it to use this feature."
            )

        url = URL.create(self.db_url)
        editor_url = f"{url.drivername}://{url.username}:{url.password}@{url.host}:{url.port}/edit/{url.database}"
        return HTML(f"<a href='{editor_url}' target='_blank'>Launch SQL Editor</a>")

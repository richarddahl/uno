import pytest
from pydantic import ValidationError
from uno.infrastructure.sql.builders.function import SQLFunctionBuilder
from uno.infrastructure.sql.builders.index import SQLIndexBuilder
from uno.infrastructure.sql.builders.trigger import SQLTriggerBuilder


# --- SQLFunctionBuilder Tests ---
def test_function_builder_success():
    sql = (
        SQLFunctionBuilder()
        .with_schema("public")
        .with_name("my_func")
        .with_args("a int, b int")
        .with_return_type("int")
        .with_body("BEGIN RETURN a + b; END;")
        .build()
    )
    assert "CREATE OR REPLACE FUNCTION public.my_func" in sql
    assert "RETURNS int" in sql
    assert "BEGIN RETURN a + b; END;" in sql


def test_function_builder_missing_required():
    builder = SQLFunctionBuilder().with_schema("public").with_name("").with_body("")
    with pytest.raises(ValidationError):
        builder.build()


# --- SQLIndexBuilder Tests ---
def test_index_builder_success():
    sql = (
        SQLIndexBuilder()
        .with_schema("public")
        .with_table("users")
        .with_name("users_email_idx")
        .with_columns(["email"])
        .unique()
        .build()
    )
    assert "CREATE UNIQUE INDEX users_email_idx" in sql
    assert "ON public.users USING btree" in sql
    assert "(email)" in sql


def test_index_builder_missing_required():
    builder = (
        SQLIndexBuilder().with_schema("").with_table("").with_name("").with_columns([])
    )
    with pytest.raises(ValidationError):
        builder.build()


# --- SQLTriggerBuilder Tests ---
def test_trigger_builder_success():
    sql = (
        SQLTriggerBuilder()
        .with_schema("public")
        .with_table("users")
        .with_name("users_update_trigger")
        .with_function("my_func")
        .with_timing("BEFORE")
        .with_operation("UPDATE")
        .build()
    )
    assert "CREATE TRIGGER users_update_trigger" in sql
    assert "BEFORE UPDATE ON public.users" in sql
    assert "EXECUTE FUNCTION my_func();" in sql


def test_trigger_builder_missing_required():
    builder = (
        SQLTriggerBuilder()
        .with_schema("")
        .with_table("")
        .with_name("")
        .with_function("")
    )
    with pytest.raises(ValidationError):
        builder.build()

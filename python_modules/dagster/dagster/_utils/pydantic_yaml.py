from typing import Type, TypeVar

from pydantic import BaseModel, ValidationError

from dagster._model.pydantic_compat_layer import build_validation_error

from .source_position import KeyPath, populate_source_position_and_key_paths
from .yaml_utils import parse_yaml_with_source_positions

T = TypeVar("T", bound=BaseModel)


def parse_yaml_file_to_pydantic(cls: Type[T], src: str, filename: str = "<string>") -> T:
    """Parse the YAML source and create a Pydantic model instance from it.

    Attaches source position information to the `_source_position_and_key_path` attribute of the
    Pydantic model instance and sub-objects.

    Args:
        cls (type[T]): The Pydantic model class to use for validation.
        src (str): The YAML source string to be parsed.
        filename (str): The filename associated with the YAML source, used for error reporting.
            Defaults to "<string>" if not provided.

    Returns:
        T: An instance of the Pydantic model class, with the `_source_position_and_key_path`
            attribute populated on it and all the objects inside it.

    Raises:
        ValidationError: If the YAML data does not conform to the Pydantic model schema. Errors
            will include context information about the position in the document that the model
            corresponds to.
    """
    parsed = parse_yaml_with_source_positions(src, filename)
    try:
        model = cls.parse_obj(parsed.value)
    except ValidationError as e:
        line_errors = []
        for error in e.errors():
            key_path: KeyPath = error["loc"]
            key_path_str = ".".join(str(part) for part in key_path)
            source_position = parsed.source_position_tree.lookup(key_path)
            line_errors.append({**error, "loc": [key_path_str + " at " + str(source_position)]})

        # `from None` avoids the confusing "During handling of the
        # above exception, another exception occurred"
        raise build_validation_error(
            base_error=e, line_errors=line_errors, input_type="json", hide_input=False
        ) from None

    populate_source_position_and_key_paths(model, parsed.source_position_tree)
    return model

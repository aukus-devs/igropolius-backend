import inspect
import json

from pydantic.json_schema import models_json_schema

import src.api_models

if __name__ == "__main__":
    base_models = []

    for name, obj in inspect.getmembers(src.api_models):
        if (
            inspect.isclass(obj)
            and issubclass(obj, src.api_models.BaseModel)
            and obj != src.api_models.BaseModel
        ):
            base_models.append((obj, "validation"))

    # Generate JSON schema for all models in the current module
    schema_dict, root_schema = models_json_schema(base_models, by_alias=False)

    # Optionally, save the schema to a file
    with open("api-schema.json", "w") as f:
        json.dump(root_schema, f, indent=2)

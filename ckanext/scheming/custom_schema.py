import os
import yaml

from pydantic import BaseModel, validator, root_validator, create_model
from pydantic.fields import ModelField, Field
from pydantic.class_validators import Validator
from typing import List, Optional

from ckan.plugins.toolkit import get_validator, config


def attach_validators_to_field(submodel, validators):
    for f_name, validators_ in validators.items():
        for validator in validators_:
            submodel.__fields__[f_name].class_validators.update({"validator": validator})


class CustomModel(BaseModel):

    class Config:
        extra = "allow"

    @classmethod
    def from_yaml(cls, file_path):
        cls.__annotations__ = {}
        with open(file_path, "r") as yaml_file:
            data = yaml.safe_load(yaml_file)

        for field_data in data.get('dataset_fields'):
            new_fields = {}
            new_annotations = {}
            class_validators = {}
            breakpoint()
            f_name = field_data['field_name']
            if 'repeating_subfields' in field_data:
                submodel_fields = {}
                repeating_subfields = field_data['repeating_subfields']
                for subfield in repeating_subfields:

                    subfield_name = subfield['field_name']
                    subfield_type = subfield.get('type', str)
                    subfield_required = ... if subfield.get('required') else None
                    subfield_validators = subfield.get('validators')

                    sub_validators = {}
                    if subfield_validators:
                        validators = subfield_validators.split()
                        for validator in validators:
                            validator_name = validator
                            pydantic_validator = f'pydantic_{validator}'

                            try:
                                validator = get_validator(pydantic_validator)
                            except:
                                validator = get_validator(validator)
                            _validator = Validator(validator)

                            if sub_validators.get(subfield_name, None):
                                sub_validators[subfield_name].append(_validator)
                            else:
                                sub_validators.update({subfield_name: [_validator]})

                    subfield_value = (subfield_type, subfield_required)
                    submodel_fields[subfield_name] = subfield_value
                # breakpoint()
                submodel = type(f_name.capitalize(), (BaseModel,), submodel_fields)
                attach_validators_to_field(submodel, sub_validators)
                new_annotations[f_name] = List[submodel]

            else:
                required = field_data.get('required', None)
                extra_validators = field_data.get('validators', None)

                if required:
                    required = ...
                type_ = (field_data.get('type', str), required)

                if isinstance(type_, tuple):
                    try:
                        f_annotation, f_value = type_
                    except ValueError as e:
                        raise Exception(
                            'field definitions should be a tuple of (<type>, <default>)'
                        ) from e
                else:
                    f_annotation, f_value = None, type_

                if f_annotation:
                    new_annotations[f_name] = f_annotation
                if extra_validators:
                    validators = extra_validators.split()

                    for validator in validators:
                        validator_name = validator
                        pydantic_validator = f'pydantic_{validator}'
                        try:
                            validator = get_validator(pydantic_validator)
                        except:
                            validator = get_validator(validator)
                        _validator = Validator(validator)
                        class_validators.update({validator_name: _validator})
                # breakpoint()
                new_fields[f_name] = ModelField.infer(name=f_name, value=f_value, annotation=f_annotation, class_validators=class_validators, config=cls.__config__)
            cls.schema().update({f_name: {'title': f_name.capitalize(), 'type': new_annotations[f_name]}})
            cls.__fields__.update(new_fields)
            cls.__annotations__.update(new_annotations)
        return cls

    # @root_validator(pre=True)
    def validate_fields(cls, values):
        breakpoint()
        # TODO

        return values


__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
dataset_schema = config.get('scheming.dataset_schemas', 'ckan_dataset.yaml').split(':')[-1]
pydantic_model = CustomModel.from_yaml(f"{__location__}/{dataset_schema}")

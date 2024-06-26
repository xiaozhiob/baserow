import abc
from typing import Any, Dict, List, Optional, TypedDict

from django.core.exceptions import ValidationError
from django.core.validators import validate_email, validate_integer
from django.db.models import IntegerField, QuerySet
from django.db.models.functions import Cast

from rest_framework import serializers
from rest_framework.exceptions import ValidationError as DRFValidationError

from baserow.contrib.builder.api.elements.serializers import DropdownOptionSerializer
from baserow.contrib.builder.elements.mixins import (
    CollectionElementTypeMixin,
    CollectionElementWithFieldsTypeMixin,
    ContainerElementTypeMixin,
    FormElementTypeMixin,
)
from baserow.contrib.builder.elements.models import (
    INPUT_TEXT_TYPES,
    WIDTHS,
    ButtonElement,
    CheckboxElement,
    ColumnElement,
    DropdownElement,
    DropdownElementOption,
    Element,
    FormContainerElement,
    HeadingElement,
    HorizontalAlignments,
    IFrameElement,
    ImageElement,
    InputTextElement,
    LinkElement,
    NavigationElementMixin,
    RepeatElement,
    TableElement,
    TextElement,
    VerticalAlignments,
)
from baserow.contrib.builder.elements.registries import (
    ElementType,
    element_type_registry,
)
from baserow.contrib.builder.formula_importer import import_formula
from baserow.contrib.builder.pages.handler import PageHandler
from baserow.contrib.builder.pages.models import Page
from baserow.contrib.builder.types import ElementDict
from baserow.core.formula.types import BaserowFormula
from baserow.core.registry import T
from baserow.core.user_files.handler import UserFileHandler


class ColumnElementType(ContainerElementTypeMixin, ElementType):
    """
    A column element is a container element that can be used to display other elements
    in a column.
    """

    type = "column"
    model_class = ColumnElement

    class SerializedDict(ElementDict):
        column_amount: int
        column_gap: int
        alignment: str

    @property
    def serializer_field_names(self):
        return super().serializer_field_names + [
            "column_amount",
            "column_gap",
            "alignment",
        ]

    @property
    def allowed_fields(self):
        return super().allowed_fields + [
            "column_amount",
            "column_gap",
            "alignment",
        ]

    def get_pytest_params(self, pytest_data_fixture) -> Dict[str, Any]:
        return {
            "column_amount": 2,
            "column_gap": 10,
            "alignment": VerticalAlignments.TOP,
        }

    def get_new_place_in_container(
        self, container_element_before_update: ColumnElement, places_removed: List[str]
    ) -> int:
        places_removed_casted = [int(place) for place in places_removed]

        if len(places_removed) == 0:
            return container_element_before_update.column_amount - 1

        return min(places_removed_casted) - 1

    def get_places_in_container_removed(
        self, values: Dict, instance: ColumnElement
    ) -> List[str]:
        column_amount = values.get("column_amount", None)

        if column_amount is None:
            return []

        places_removed = list(range(column_amount, instance.column_amount))

        return [str(place) for place in places_removed]

    def apply_order_by_children(self, queryset: QuerySet[Element]) -> QuerySet[Element]:
        return queryset.annotate(
            place_in_container_as_int=Cast(
                "place_in_container", output_field=IntegerField()
            )
        ).order_by("place_in_container_as_int", "order")

    def validate_place_in_container(
        self, place_in_container: str, instance: ColumnElement
    ):
        max_place_in_container = instance.column_amount - 1
        if int(place_in_container) > max_place_in_container:
            raise DRFValidationError(
                f"place_in_container can at most be {max_place_in_container}, ({place_in_container}, was given)"
            )


class FormContainerElementType(ContainerElementTypeMixin, ElementType):
    type = "form_container"
    model_class = FormContainerElement
    allowed_fields = [
        "submit_button_label",
        "button_color",
        "reset_initial_values_post_submission",
    ]
    serializer_field_names = [
        "submit_button_label",
        "button_color",
        "reset_initial_values_post_submission",
    ]

    class SerializedDict(ElementDict):
        button_color: str
        submit_button_label: BaserowFormula
        reset_initial_values_post_submission: bool

    def get_pytest_params(self, pytest_data_fixture) -> Dict[str, Any]:
        return {
            "submit_button_label": "'Submit'",
            "reset_initial_values_post_submission": True,
        }

    @property
    def serializer_field_overrides(self):
        from baserow.core.formula.serializers import FormulaSerializerField

        return {
            "submit_button_label": FormulaSerializerField(
                help_text=FormContainerElement._meta.get_field(
                    "submit_button_label"
                ).help_text,
                required=False,
                allow_blank=True,
                default="",
            ),
            "button_color": serializers.CharField(
                max_length=20,
                required=False,
                default="primary",
                help_text="Button color.",
            ),
            "reset_initial_values_post_submission": serializers.BooleanField(
                help_text=FormContainerElement._meta.get_field(
                    "reset_initial_values_post_submission"
                ).help_text,
                required=False,
            ),
        }

    @property
    def child_types_allowed(self) -> List[str]:
        child_types_allowed = []

        for element_type in element_type_registry.get_all():
            if isinstance(element_type, FormElementTypeMixin):
                child_types_allowed.append(element_type.type)

        return child_types_allowed

    def import_serialized(
        self,
        page,
        serialized_values,
        id_mapping,
        files_zip=None,
        storage=None,
        cache=None,
    ):
        serialized_copy = serialized_values.copy()
        if serialized_copy["submit_button_label"]:
            serialized_copy["submit_button_label"] = import_formula(
                serialized_copy["submit_button_label"], id_mapping
            )

        return super().import_serialized(
            page,
            serialized_copy,
            id_mapping,
            files_zip=files_zip,
            storage=storage,
            cache=cache,
        )


class TableElementType(CollectionElementWithFieldsTypeMixin, ElementType):
    type = "table"
    model_class = TableElement

    class SerializedDict(CollectionElementWithFieldsTypeMixin.SerializedDict):
        button_color: str

    @property
    def allowed_fields(self):
        return super().allowed_fields + ["button_color"]

    @property
    def serializer_field_names(self):
        return super().serializer_field_names + ["button_color"]

    @property
    def serializer_field_overrides(self):
        return {
            **super().serializer_field_overrides,
            "button_color": serializers.CharField(
                max_length=20,
                required=False,
                default="primary",
                help_text="Button color.",
            ),
        }

    def get_pytest_params(self, pytest_data_fixture) -> Dict[str, Any]:
        return {"data_source_id": None}


class RepeatElementType(
    CollectionElementTypeMixin, ContainerElementTypeMixin, ElementType
):
    type = "repeat"
    model_class = RepeatElement

    @property
    def allowed_fields(self):
        return super().allowed_fields + ["orientation", "items_per_row"]

    @property
    def serializer_field_names(self):
        return super().serializer_field_names + ["orientation", "items_per_row"]

    class SerializedDict(
        CollectionElementTypeMixin.SerializedDict,
        ContainerElementTypeMixin.SerializedDict,
    ):
        orientation: str
        items_per_row: dict

    def get_pytest_params(self, pytest_data_fixture) -> Dict[str, Any]:
        return {
            "data_source_id": None,
            "orientation": RepeatElement.ORIENTATIONS.VERTICAL,
        }


class HeadingElementType(ElementType):
    """
    A simple heading element that can be used to display a title.
    """

    type = "heading"
    model_class = HeadingElement
    serializer_field_names = ["value", "level", "font_color", "alignment"]
    allowed_fields = ["value", "level", "font_color", "alignment"]

    class SerializedDict(ElementDict):
        value: BaserowFormula
        font_color: str
        level: int
        alignment: str

    @property
    def serializer_field_overrides(self):
        from baserow.core.formula.serializers import FormulaSerializerField

        overrides = {
            "value": FormulaSerializerField(
                help_text="The value of the element. Must be an formula.",
                required=False,
                allow_blank=True,
                default="",
            ),
            "level": serializers.IntegerField(
                help_text="The level of the heading from 1 to 6.",
                min_value=1,
                max_value=6,
                default=1,
            ),
            "font_color": serializers.CharField(
                max_length=20,
                required=False,
                allow_blank=True,
                help_text="Heading font color.",
            ),
        }

        return overrides

    def get_pytest_params(self, pytest_data_fixture):
        return {"value": "'Corporis perspiciatis'", "level": 2, "alignment": "left"}

    def import_serialized(
        self,
        page,
        serialized_values,
        id_mapping,
        files_zip=None,
        storage=None,
        cache=None,
    ):
        serialized_copy = serialized_values.copy()
        if serialized_copy["value"]:
            serialized_copy["value"] = import_formula(
                serialized_copy["value"], id_mapping
            )

        return super().import_serialized(
            page,
            serialized_copy,
            id_mapping,
            files_zip=files_zip,
            storage=storage,
            cache=cache,
        )


class TextElementType(ElementType):
    """
    A text element that allows plain or markdown content.
    """

    type = "text"
    model_class = TextElement
    serializer_field_names = ["value", "alignment", "format"]
    allowed_fields = ["value", "alignment", "format"]

    class SerializedDict(ElementDict):
        value: BaserowFormula
        alignment: str
        format: str

    def get_pytest_params(self, pytest_data_fixture):
        return {
            "value": "'Suscipit maxime eos ea vel commodi dolore. "
            "Eum dicta sit rerum animi. Sint sapiente eum cupiditate nobis vel. "
            "Maxime qui nam consequatur. "
            "Asperiores corporis perspiciatis nam harum veritatis. "
            "Impedit qui maxime aut illo quod ea molestias.'",
            "alignment": "left",
            "format": TextElement.TEXT_FORMATS.PLAIN,
        }

    @property
    def serializer_field_overrides(self):
        from baserow.core.formula.serializers import FormulaSerializerField

        return {
            "value": FormulaSerializerField(
                help_text="The value of the element. Must be a formula.",
                required=False,
                allow_blank=True,
                default="",
            ),
            "format": serializers.ChoiceField(
                choices=TextElement.TEXT_FORMATS.choices,
                default=TextElement.TEXT_FORMATS.PLAIN,
                help_text=TextElement._meta.get_field("format").help_text,
            ),
        }

    def import_serialized(
        self,
        page,
        serialized_values,
        id_mapping,
        files_zip=None,
        storage=None,
        cache=None,
    ):
        serialized_copy = serialized_values.copy()
        if serialized_copy["value"]:
            serialized_copy["value"] = import_formula(
                serialized_copy["value"], id_mapping
            )

        return super().import_serialized(
            page,
            serialized_copy,
            id_mapping,
            files_zip=files_zip,
            storage=storage,
            cache=cache,
        )


class NavigationElementManager:
    """
    A base class that adds navigation properties to an element. (not an actual element)
    """

    def __init__(self, type=None):
        self.type = type

    serializer_field_names = [
        "navigation_type",
        "navigate_to_page_id",
        "navigate_to_url",
        "page_parameters",
        "target",
    ]
    allowed_fields = [
        "navigation_type",
        "navigate_to_page_id",
        "navigate_to_url",
        "page_parameters",
        "target",
    ]

    class SerializedDict(TypedDict):
        navigation_type: str
        navigate_to_page_id: int
        page_parameters: List
        navigate_to_url: BaserowFormula
        target: str

    def deserialize_property(
        self,
        prop_name: str,
        value: Any,
        id_mapping: Dict[str, Any],
        **kwargs,
    ) -> Any:
        if prop_name == "navigate_to_page_id" and value:
            return id_mapping["builder_pages"][value]

        if prop_name == "navigate_to_url":
            return import_formula(value, id_mapping, **kwargs)

        if prop_name == "page_parameters":
            return [
                {
                    **p,
                    "value": import_formula(p["value"], id_mapping, **kwargs),
                }
                for p in value
            ]

        return value

    @property
    def serializer_field_overrides(self):
        from baserow.contrib.builder.api.elements.serializers import (
            PageParameterValueSerializer,
        )
        from baserow.core.formula.serializers import FormulaSerializerField

        overrides = {
            "navigation_type": serializers.ChoiceField(
                choices=NavigationElementMixin.NAVIGATION_TYPES.choices,
                help_text=LinkElement._meta.get_field("navigation_type").help_text,
                required=False,
            ),
            "navigate_to_page_id": serializers.IntegerField(
                allow_null=True,
                default=None,
                help_text=LinkElement._meta.get_field("navigate_to_page").help_text,
                required=False,
            ),
            "navigate_to_url": FormulaSerializerField(
                help_text=LinkElement._meta.get_field("navigate_to_url").help_text,
                default="",
                allow_blank=True,
                required=False,
            ),
            "page_parameters": PageParameterValueSerializer(
                many=True,
                help_text=LinkElement._meta.get_field("page_parameters").help_text,
                required=False,
            ),
            "target": serializers.ChoiceField(
                choices=NavigationElementMixin.TARGETS.choices,
                help_text=LinkElement._meta.get_field("target").help_text,
                required=False,
            ),
        }
        return overrides

    @classmethod
    def get_serializer_field_overrides(cls):
        return cls().serializer_field_overrides

    def get_pytest_params(self, pytest_data_fixture):
        return {
            "navigation_type": "custom",
            "navigate_to_page_id": None,
            "navigate_to_url": '"http://example.com"',
            "page_parameters": [],
            "target": "blank",
        }

    def prepare_value_for_db(
        self, values: Dict, instance: Optional[LinkElement] = None
    ):
        """
        set the type of the element for the prepare_value_for_db method in case we're
        adding to a parent element which requires a type check
        """

        page_params = values.get("page_parameters", [])
        navigate_to_page_id = values.get(
            "navigate_to_page_id", getattr(instance, "navigate_to_page_id", None)
        )

        if len(page_params) != 0 and navigate_to_page_id is not None:
            page = (
                PageHandler().get_page(navigate_to_page_id)
                if navigate_to_page_id is not None
                else instance.navigate_to_page
            )

            self._raise_if_path_params_are_invalid(page_params, page)

        return ElementType.prepare_value_for_db(self, values, instance)

    def _raise_if_path_params_are_invalid(self, path_params: Dict, page: Page) -> None:
        """
        Checks if the path parameters being set are correctly correlated to the
        path parameters defined for the page.

        :param path_params: The path params defined for the navigation event
        :param page: The page the element is navigating to
        :raises DRFValidationError: If the param does not exist or the
            type does not match
        """

        parameter_types = {p["name"]: p["type"] for p in page.path_params}

        for page_parameter in path_params:
            page_parameter_name = page_parameter["name"]
            page_parameter_type = parameter_types.get(page_parameter_name, None)

            if page_parameter_type is None:
                raise DRFValidationError(
                    f"Page path parameter {page_parameter} does not exist."
                )


class LinkElementType(ElementType):
    """
    A simple paragraph element that can be used to display a paragraph of text.
    """

    type = "link"
    model_class = LinkElement
    PATH_PARAM_TYPE_TO_PYTHON_TYPE_MAP = {"text": str, "numeric": int}

    @property
    def serializer_field_names(self):
        return (
            super().serializer_field_names
            + NavigationElementManager.serializer_field_names
            + [
                "value",
                "variant",
                "width",
                "alignment",
                "button_color",
            ]
        )

    @property
    def allowed_fields(self):
        return (
            super().allowed_fields
            + NavigationElementManager.allowed_fields
            + [
                "value",
                "variant",
                "width",
                "alignment",
                "button_color",
            ]
        )

    class SerializedDict(ElementDict, NavigationElementManager.SerializedDict):
        value: BaserowFormula
        variant: str
        width: str
        alignment: str
        button_color: str

    def deserialize_property(
        self,
        prop_name: str,
        value: Any,
        id_mapping: Dict[str, Any],
        files_zip=None,
        storage=None,
        cache=None,
        **kwargs,
    ) -> Any:
        if prop_name == "value":
            return import_formula(value, id_mapping)

        return super().deserialize_property(
            prop_name,
            NavigationElementManager().deserialize_property(
                prop_name,
                value,
                id_mapping,
            ),
            id_mapping,
            files_zip=files_zip,
            storage=storage,
            cache=cache,
            **kwargs,
        )

    @property
    def serializer_field_overrides(self):
        from baserow.core.formula.serializers import FormulaSerializerField

        overrides = (
            super().serializer_field_overrides
            | NavigationElementManager().get_serializer_field_overrides()
            | {
                "value": FormulaSerializerField(
                    help_text="The value of the element. Must be an formula.",
                    required=False,
                    allow_blank=True,
                    default="",
                ),
                "variant": serializers.ChoiceField(
                    choices=LinkElement.VARIANTS.choices,
                    help_text=LinkElement._meta.get_field("variant").help_text,
                    required=False,
                ),
                "width": serializers.ChoiceField(
                    choices=WIDTHS.choices,
                    help_text=LinkElement._meta.get_field("width").help_text,
                    required=False,
                ),
                "alignment": serializers.ChoiceField(
                    choices=HorizontalAlignments.choices,
                    help_text=LinkElement._meta.get_field("alignment").help_text,
                    required=False,
                ),
                "button_color": serializers.CharField(
                    max_length=20,
                    required=False,
                    default="primary",
                    help_text="Button color.",
                ),
            }
        )
        return overrides

    def get_pytest_params(self, pytest_data_fixture):
        return NavigationElementManager().get_pytest_params(pytest_data_fixture) | {
            "value": "'test'",
            "variant": "link",
            "width": "auto",
            "alignment": "center",
        }

    def prepare_value_for_db(
        self, values: Dict, instance: Optional[LinkElement] = None
    ):
        return NavigationElementManager(self.type).prepare_value_for_db(
            values, instance
        )


class ImageElementType(ElementType):
    """
    A simple image element that can display an image either through a remote source
    or via an uploaded file
    """

    type = "image"
    model_class = ImageElement
    serializer_field_names = [
        "image_source_type",
        "image_file",
        "image_url",
        "alt_text",
        "alignment",
        "style_image_constraint",
        "style_max_width",
        "style_max_height",
    ]
    request_serializer_field_names = [
        "image_source_type",
        "image_file",
        "image_url",
        "alt_text",
        "alignment",
        "style_image_constraint",
        "style_max_width",
        "style_max_height",
    ]
    allowed_fields = [
        "image_source_type",
        "image_file",
        "image_url",
        "alt_text",
        "alignment",
        "style_image_constraint",
        "style_max_width",
        "style_max_height",
    ]

    class SerializedDict(ElementDict):
        image_source_type: str
        image_file_id: int
        image_url: BaserowFormula
        alt_text: BaserowFormula
        alignment: str
        style_image_constraint: str
        style_max_width: Optional[int]
        style_max_height: Optional[int]

    def get_pytest_params(self, pytest_data_fixture):
        return {
            "image_source_type": ImageElement.IMAGE_SOURCE_TYPES.UPLOAD,
            "image_file_id": None,
            "image_url": "'https://test.com/image.png'",
            "alt_text": "'some alt text'",
            "alignment": HorizontalAlignments.LEFT,
            "style_image_constraint": "",
            "style_max_width": None,
            "style_max_height": None,
        }

    @property
    def serializer_field_overrides(self):
        from baserow.api.user_files.serializers import UserFileSerializer
        from baserow.core.formula.serializers import FormulaSerializerField

        overrides = {
            "image_file": UserFileSerializer(required=False),
            "image_url": FormulaSerializerField(
                help_text=ImageElement._meta.get_field("image_url").help_text,
                required=False,
                allow_blank=True,
                default="",
            ),
            "alt_text": FormulaSerializerField(
                help_text=ImageElement._meta.get_field("alt_text").help_text,
                required=False,
                allow_blank=True,
                default="",
            ),
        }

        overrides.update(super().serializer_field_overrides)
        return overrides

    @property
    def request_serializer_field_overrides(self):
        from baserow.api.user_files.serializers import UserFileField
        from baserow.contrib.builder.api.validators import image_file_validation

        overrides = {
            "image_file": UserFileField(
                allow_null=True,
                required=False,
                default=None,
                help_text="The image file",
                validators=[image_file_validation],
            ),
            "alignment": serializers.ChoiceField(
                choices=HorizontalAlignments.choices,
                help_text=ImageElement._meta.get_field("alignment").help_text,
                required=False,
            ),
            "style_max_width": serializers.IntegerField(
                required=False,
                allow_null=ImageElement._meta.get_field("style_max_width").null,
                default=ImageElement._meta.get_field("style_max_width").default,
                help_text=ImageElement._meta.get_field("style_max_width").help_text,
            ),
        }
        if super().request_serializer_field_overrides is not None:
            overrides.update(super().request_serializer_field_overrides)
        return overrides

    def serialize_property(
        self,
        element: Element,
        prop_name: BaserowFormula,
        files_zip=None,
        storage=None,
        cache=None,
    ):
        if prop_name == "image_file_id":
            return UserFileHandler().export_user_file(
                element.image_file, files_zip=files_zip, storage=storage, cache=cache
            )

        return super().serialize_property(
            element, prop_name, files_zip=files_zip, storage=storage, cache=cache
        )

    def deserialize_property(
        self,
        prop_name: str,
        value: Any,
        id_mapping: Dict[str, Any],
        files_zip=None,
        storage=None,
        cache=None,
        **kwargs,
    ) -> Any:
        if prop_name == "image_url":
            return import_formula(value, id_mapping)

        if prop_name == "alt_text":
            return import_formula(value, id_mapping)

        if prop_name == "image_file_id":
            user_file = UserFileHandler().import_user_file(
                value, files_zip=files_zip, storage=storage
            )
            if user_file:
                return user_file.id
            return None

        return super().deserialize_property(
            prop_name,
            value,
            id_mapping,
            files_zip=files_zip,
            storage=storage,
            cache=cache,
            **kwargs,
        )


class InputElementType(FormElementTypeMixin, ElementType, abc.ABC):
    pass


class InputTextElementType(InputElementType):
    type = "input_text"
    model_class = InputTextElement
    allowed_fields = [
        "label",
        "default_value",
        "required",
        "validation_type",
        "placeholder",
        "is_multiline",
        "rows",
        "input_type",
    ]
    serializer_field_names = [
        "label",
        "default_value",
        "required",
        "validation_type",
        "placeholder",
        "is_multiline",
        "rows",
        "input_type",
    ]

    class SerializedDict(ElementDict):
        label: BaserowFormula
        required: bool
        validation_type: str
        placeholder: str
        default_value: BaserowFormula
        is_multiline: bool
        rows: int
        input_type: str

    @property
    def serializer_field_overrides(self):
        from baserow.core.formula.serializers import FormulaSerializerField

        overrides = {
            "label": FormulaSerializerField(
                help_text=InputTextElement._meta.get_field("label").help_text,
                required=False,
                allow_blank=True,
                default="",
            ),
            "default_value": FormulaSerializerField(
                help_text=InputTextElement._meta.get_field("default_value").help_text,
                required=False,
                allow_blank=True,
                default="",
            ),
            "required": serializers.BooleanField(
                help_text=InputTextElement._meta.get_field("required").help_text,
                default=False,
                required=False,
            ),
            "placeholder": FormulaSerializerField(
                help_text=InputTextElement._meta.get_field("placeholder").help_text,
                required=False,
                allow_blank=True,
                default="",
            ),
            "is_multiline": serializers.BooleanField(
                help_text=InputTextElement._meta.get_field("is_multiline").help_text,
                required=False,
                default=False,
            ),
            "rows": serializers.IntegerField(
                help_text=InputTextElement._meta.get_field("rows").help_text,
                required=False,
                default=3,
                min_value=1,
                max_value=100,
            ),
            "input_type": serializers.ChoiceField(
                choices=INPUT_TEXT_TYPES.choices,
                help_text=InputTextElement._meta.get_field("input_type").help_text,
                required=False,
                default=INPUT_TEXT_TYPES.TEXT,
            ),
        }

        return overrides

    def import_serialized(
        self,
        page,
        serialized_values,
        id_mapping,
        files_zip=None,
        storage=None,
        cache=None,
    ):
        serialized_copy = serialized_values.copy()
        if serialized_copy["label"]:
            serialized_copy["label"] = import_formula(
                serialized_copy["label"], id_mapping
            )
        if serialized_copy["default_value"]:
            serialized_copy["default_value"] = import_formula(
                serialized_copy["default_value"], id_mapping
            )
        if serialized_copy["placeholder"]:
            serialized_copy["placeholder"] = import_formula(
                serialized_copy["placeholder"], id_mapping
            )

        return super().import_serialized(
            page,
            serialized_copy,
            id_mapping,
            files_zip=files_zip,
            storage=storage,
            cache=cache,
        )

    def get_pytest_params(self, pytest_data_fixture):
        return {
            "label": "",
            "required": False,
            "placeholder": "",
            "default_value": "'Corporis perspiciatis'",
            "is_multiline": False,
            "rows": 1,
            "input_type": "text",
        }

    def is_valid(self, element: InputTextElement, value: Any) -> bool:
        """
        :param element: The element we're trying to use form data in.
        :param value: The form data value, which may be invalid.
        :return: Whether the value is valid or not for this element.
        """

        if not value:
            return element.required is False

        if element.validation_type == "integer":
            try:
                validate_integer(value)
            except ValidationError:
                return False
        elif element.validation_type == "email":
            try:
                validate_email(value)
            except ValidationError:
                return False
        return True


class ButtonElementType(ElementType):
    type = "button"
    model_class = ButtonElement
    allowed_fields = ["value", "alignment", "width", "button_color"]
    serializer_field_names = ["value", "alignment", "width", "button_color"]

    class SerializedDict(ElementDict):
        value: BaserowFormula
        width: str
        alignment: str
        button_color: str

    @property
    def serializer_field_overrides(self):
        from baserow.core.formula.serializers import FormulaSerializerField

        overrides = {
            "value": FormulaSerializerField(
                help_text=ButtonElement._meta.get_field("value").help_text,
                required=False,
                allow_blank=True,
                default="",
            ),
            "width": serializers.ChoiceField(
                choices=WIDTHS.choices,
                help_text=ButtonElement._meta.get_field("width").help_text,
                required=False,
            ),
            "alignment": serializers.ChoiceField(
                choices=HorizontalAlignments.choices,
                help_text=ButtonElement._meta.get_field("alignment").help_text,
                required=False,
            ),
            "button_color": serializers.CharField(
                max_length=20,
                required=False,
                default="primary",
                help_text="Button color.",
            ),
        }

        return overrides

    def get_pytest_params(self, pytest_data_fixture) -> Dict[str, Any]:
        return {"value": "'Some value'"}

    def import_serialized(
        self,
        page,
        serialized_values,
        id_mapping,
        files_zip=None,
        storage=None,
        cache=None,
    ):
        serialized_copy = serialized_values.copy()
        if serialized_copy["value"]:
            serialized_copy["value"] = import_formula(
                serialized_copy["value"], id_mapping
            )

        return super().import_serialized(
            page,
            serialized_copy,
            id_mapping,
            files_zip=files_zip,
            storage=storage,
            cache=cache,
        )


class CheckboxElementType(InputElementType):
    type = "checkbox"
    model_class = CheckboxElement
    allowed_fields = ["label", "default_value", "required"]
    serializer_field_names = ["label", "default_value", "required"]

    class SerializedDict(ElementDict):
        label: BaserowFormula
        required: bool
        default_value: BaserowFormula

    @property
    def serializer_field_overrides(self):
        from baserow.core.formula.serializers import FormulaSerializerField

        overrides = {
            "label": FormulaSerializerField(
                help_text=CheckboxElement._meta.get_field("label").help_text,
                required=False,
                allow_blank=True,
                default="",
            ),
            "default_value": FormulaSerializerField(
                help_text=CheckboxElement._meta.get_field("default_value").help_text,
                required=False,
                allow_blank=True,
                default="",
            ),
            "required": serializers.BooleanField(
                help_text=CheckboxElement._meta.get_field("required").help_text,
                default=False,
                required=False,
            ),
        }

        return overrides

    def import_serialized(
        self,
        page,
        serialized_values,
        id_mapping,
        files_zip=None,
        storage=None,
        cache=None,
    ):
        serialized_copy = serialized_values.copy()
        if serialized_copy["label"]:
            serialized_copy["label"] = import_formula(
                serialized_copy["label"], id_mapping
            )
        if serialized_copy["default_value"]:
            serialized_copy["default_value"] = import_formula(
                serialized_copy["default_value"], id_mapping
            )

        return super().import_serialized(
            page,
            serialized_copy,
            id_mapping,
            files_zip=files_zip,
            storage=storage,
            cache=cache,
        )

    def get_pytest_params(self, pytest_data_fixture):
        return {
            "label": "",
            "required": False,
            "default_value": "",
        }


class DropdownElementType(FormElementTypeMixin, ElementType):
    type = "dropdown"
    model_class = DropdownElement
    allowed_fields = ["label", "default_value", "required", "placeholder"]
    serializer_field_names = [
        "label",
        "default_value",
        "required",
        "placeholder",
        "options",
    ]
    request_serializer_field_names = [
        "label",
        "default_value",
        "required",
        "placeholder",
        "options",
    ]

    class SerializedDict(ElementDict):
        label: BaserowFormula
        required: bool
        placeholder: BaserowFormula
        default_value: BaserowFormula
        options: List

    @property
    def serializer_field_overrides(self):
        from baserow.core.formula.serializers import FormulaSerializerField

        overrides = {
            "label": FormulaSerializerField(
                help_text=DropdownElement._meta.get_field("label").help_text,
                required=False,
                allow_blank=True,
                default="",
            ),
            "default_value": FormulaSerializerField(
                help_text=DropdownElement._meta.get_field("default_value").help_text,
                required=False,
                allow_blank=True,
                default="",
            ),
            "required": serializers.BooleanField(
                help_text=DropdownElement._meta.get_field("required").help_text,
                default=False,
                required=False,
            ),
            "placeholder": serializers.CharField(
                help_text=DropdownElement._meta.get_field("placeholder").help_text,
                required=False,
                allow_blank=True,
                default="",
            ),
            "options": DropdownOptionSerializer(
                source="dropdownelementoption_set", many=True, required=False
            ),
        }

        return overrides

    @property
    def request_serializer_field_overrides(self):
        return {
            **self.serializer_field_overrides,
            "options": DropdownOptionSerializer(many=True, required=False),
        }

    def serialize_property(
        self,
        element: DropdownElement,
        prop_name: str,
        files_zip=None,
        storage=None,
        cache=None,
    ):
        if prop_name == "options":
            return [
                self.serialize_option(option)
                for option in element.dropdownelementoption_set.all()
            ]

        return super().serialize_property(
            element, prop_name, files_zip=files_zip, storage=storage, cache=cache
        )

    def deserialize_property(
        self,
        prop_name: str,
        value: Any,
        id_mapping: Dict[str, Any],
        files_zip=None,
        storage=None,
        cache=None,
        **kwargs,
    ) -> Any:
        if prop_name == "default_value":
            return import_formula(value, id_mapping)

        if prop_name == "placeholder":
            return import_formula(value, id_mapping)

        return super().deserialize_property(
            prop_name,
            value,
            id_mapping,
            files_zip=files_zip,
            storage=storage,
            cache=cache,
            **kwargs,
        )

    def import_serialized(
        self,
        parent: Any,
        serialized_values: Dict[str, Any],
        id_mapping: Dict[str, Dict[int, int]],
        files_zip=None,
        storage=None,
        cache=None,
        **kwargs,
    ) -> T:
        dropdown_element = super().import_serialized(
            parent,
            serialized_values,
            id_mapping,
            files_zip=files_zip,
            storage=storage,
            cache=cache,
        )

        options = []
        for option in serialized_values.get("options", []):
            option["dropdown_id"] = dropdown_element.id
            option_deserialized = self.deserialize_option(option)
            options.append(option_deserialized)

        DropdownElementOption.objects.bulk_create(options)

        return dropdown_element

    def create_instance_from_serialized(
        self,
        serialized_values: Dict[str, Any],
        files_zip=None,
        storage=None,
        cache=None,
        **kwargs,
    ) -> T:
        serialized_values.pop("options", None)
        return super().create_instance_from_serialized(
            serialized_values,
            files_zip=files_zip,
            storage=storage,
            cache=cache,
            **kwargs,
        )

    def serialize_option(self, option: DropdownElementOption) -> Dict:
        return {
            "value": option.value,
            "name": option.name,
            "dropdown_id": option.dropdown_id,
        }

    def deserialize_option(self, value: Dict):
        return DropdownElementOption(**value)

    def get_pytest_params(self, pytest_data_fixture) -> Dict[str, Any]:
        return {
            "label": "'test'",
            "default_value": "'option 1'",
            "required": False,
            "placeholder": "'some placeholder'",
        }

    def after_create(self, instance: DropdownElement, values: Dict):
        options = values.get("options", [])

        DropdownElementOption.objects.bulk_create(
            [DropdownElementOption(dropdown=instance, **option) for option in options]
        )

    def after_update(self, instance: DropdownElement, values: Dict):
        options = values.get("options", None)

        if options is not None:
            DropdownElementOption.objects.filter(dropdown=instance).delete()
            DropdownElementOption.objects.bulk_create(
                [
                    DropdownElementOption(dropdown=instance, **option)
                    for option in options
                ]
            )

    def is_valid(self, element: DropdownElement, value: Any) -> bool:
        """
        Responsible for validating `DropdownElement` form data. We handle
        this validation a little differently to ensure that if someone creates
        an option with a blank value, it's considered valid.

        :param element: The dropdown element.
        :param value: The dropdown value we want to validate.
        :return: Whether the value is valid or not for this element.
        """

        validOption = element.dropdownelementoption_set.filter(value=value).exists()
        return not (element.required and not validOption)


class IFrameElementType(ElementType):
    type = "iframe"
    model_class = IFrameElement
    allowed_fields = ["source_type", "url", "embed", "height"]
    serializer_field_names = ["source_type", "url", "embed", "height"]

    class SerializedDict(ElementDict):
        source_type: str
        url: BaserowFormula
        embed: BaserowFormula
        height: int

    @property
    def serializer_field_overrides(self):
        from baserow.core.formula.serializers import FormulaSerializerField

        overrides = {
            "source_type": serializers.ChoiceField(
                help_text=IFrameElement._meta.get_field("source_type").help_text,
                required=False,
                choices=IFrameElement.IFRAME_SOURCE_TYPE.choices,
                default=IFrameElement.IFRAME_SOURCE_TYPE.URL,
            ),
            "url": FormulaSerializerField(
                help_text=IFrameElement._meta.get_field("url").help_text,
                required=False,
                allow_blank=True,
                default="",
            ),
            "embed": FormulaSerializerField(
                help_text=IFrameElement._meta.get_field("embed").help_text,
                required=False,
                allow_blank=True,
                default="",
            ),
            "height": serializers.IntegerField(
                help_text=IFrameElement._meta.get_field("height").help_text,
                required=False,
                default=300,
                min_value=1,
                max_value=2000,
            ),
        }

        return overrides

    def import_serialized(
        self,
        page,
        serialized_values,
        id_mapping,
        files_zip=None,
        storage=None,
        cache=None,
    ):
        serialized_copy = serialized_values.copy()
        if serialized_copy["url"]:
            serialized_copy["url"] = import_formula(serialized_copy["url"], id_mapping)
        if serialized_copy["embed"]:
            serialized_copy["embed"] = import_formula(
                serialized_copy["embed"], id_mapping
            )

        return super().import_serialized(
            page,
            serialized_copy,
            id_mapping,
            files_zip=files_zip,
            storage=storage,
            cache=cache,
        )

    def get_pytest_params(self, pytest_data_fixture):
        return {
            "source_type": IFrameElement.IFRAME_SOURCE_TYPE.URL,
            "url": "",
            "embed": "",
            "height": 300,
        }

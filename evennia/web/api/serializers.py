"""
Serializers in the Django Rest Framework are similar to Forms in normal django.
They're used for transmitting and validating data, both going to clients and
coming to the server. However, where forms often contained presentation logic,
such as specifying widgets to use for selection, serializers typically leave
those decisions in the hands of clients, and are more focused on converting
data from the server to JSON (serialization) for a response, and validating
and converting JSON data sent from clients to our enpoints into python objects,
often django model instances, that we can use (deserialization).
"""

from rest_framework import serializers

from evennia.objects.objects import DefaultObject
from evennia.accounts.accounts import DefaultAccount
from evennia.scripts.models import ScriptDB
from evennia.typeclasses.attributes import Attribute
from evennia.typeclasses.tags import Tag


class AttributeSerializer(serializers.ModelSerializer):
    value_display = serializers.SerializerMethodField(source="value")
    db_value = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = Attribute
        fields = ["db_key", "db_category", "db_attrtype", "value_display", "db_value"]

    @staticmethod
    def get_value_display(obj: Attribute) -> str:
        """
        Gets the string display of an Attribute's value for serialization
        Args:
            obj: Attribute being serialized

        Returns:
            The Attribute's value in string format
        """
        if obj.db_strvalue:
            return obj.db_strvalue
        return str(obj.value)


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ["db_key", "db_category", "db_data", "db_tagtype"]


class SimpleObjectDBSerializer(serializers.ModelSerializer):
    class Meta:
        model = DefaultObject
        fields = ["id", "db_key"]


class TypeclassSerializerMixin(object):
    """Mixin that contains types shared by typeclasses. A note about tags, aliases, and permissions. You
    might note that the methods and fields are defined here, but they're included explicitly in each child
    class. What gives? It's a DRF error: serializer method fields which are inherited do not resolve correctly
    in child classes, and as of this current version (3.11) you must have them in the child classes explicitly
    to avoid field errors. Similarly, the child classes must contain the attribute serializer explicitly to
    not have them render PK-related fields.
    """

    shared_fields = ["id", "db_key", "db_attributes", "db_typeclass_path", "aliases", "tags", "permissions"]

    def get_tags(self, obj):
        """
        Serializes tags from the object's Tagshandler
        Args:
            obj: Typeclassed object being serialized

        Returns:
            List of TagSerializer data
        """
        return TagSerializer(obj.tags.get(return_tagobj=True, return_list=True), many=True).data

    def get_aliases(self, obj):
        """
        Serializes tags from the object's Aliashandler
        Args:
            obj: Typeclassed object being serialized

        Returns:
            List of TagSerializer data
        """
        return TagSerializer(obj.aliases.get(return_tagobj=True, return_list=True), many=True).data

    def get_permissions(self, obj):
        """
        Serializes tags from the object's Permissionshandler
        Args:
            obj: Typeclassed object being serialized

        Returns:
            List of TagSerializer data
        """
        return TagSerializer(obj.permissions.get(return_tagobj=True, return_list=True), many=True).data


class ObjectDBSerializer(TypeclassSerializerMixin, serializers.ModelSerializer):
    db_attributes = AttributeSerializer(many=True, read_only=True)
    contents = serializers.SerializerMethodField()
    exits = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()
    aliases = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = DefaultObject
        fields = ["db_location", "db_home", "contents", "exits"] + TypeclassSerializerMixin.shared_fields
        read_only_fields = ["id", "db_attributes"]

    def get_exits(self, obj):
        """
        Gets exits for the object
        Args:
            obj: Object being serialized

        Returns:
            List of data from SimpleObjectDBSerializer
        """
        exits = [ob for ob in obj.contents if ob.destination]
        return SimpleObjectDBSerializer(exits, many=True).data

    def get_contents(self, obj):
        """
        Gets non-exits for the object
        Args:
            obj: Object being serialized

        Returns:
            List of data from SimpleObjectDBSerializer
        """
        non_exits = [ob for ob in obj.contents if not ob.destination]
        return SimpleObjectDBSerializer(non_exits, many=True).data


class AccountSerializer(TypeclassSerializerMixin, serializers.ModelSerializer):
    """This uses the DefaultAccount object to have access to the sessions property"""
    db_attributes = AttributeSerializer(many=True, read_only=True)
    db_key = serializers.CharField(required=False)
    session_ids = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()
    aliases = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField()

    def get_session_ids(self, obj):
        """
        Gets a list of session IDs connected to this Account
        Args:
            obj (DefaultAccount): Account we're grabbing sessions from

        Returns:
            List of session IDs
        """
        return [sess.sessid for sess in obj.sessions.all() if hasattr(sess, "sessid")]

    class Meta:
        model = DefaultAccount
        fields = ["username", "session_ids"] + TypeclassSerializerMixin.shared_fields
        read_only_fields = ["id", "db_attributes", "db_tags", "session_ids"]


class ScriptDBSerializer(TypeclassSerializerMixin, serializers.ModelSerializer):
    db_attributes = AttributeSerializer(many=True, read_only=True)
    tags = serializers.SerializerMethodField()
    aliases = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = ScriptDB
        fields = ["db_interval", "db_persistent", "db_start_delay",
                  "db_is_active", "db_repeats"] + TypeclassSerializerMixin.shared_fields
        read_only_fields = ["id", "db_attributes", "db_tags"]

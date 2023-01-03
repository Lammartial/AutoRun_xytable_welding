"""
Customized JSON converter.
We use this converter to generate human editable JSON files that can be used 
as control parameter file in situations where a daqtabase online connection is not available or suitable.
"""
import json
import inspect

#--------------------------------------------------------------------------------------------------
def convert_to_dict(obj):
    """
    A function takes in a custom object and returns a dictionary representation of the object.
    This dict representation includes meta data such as the object's module and class names.
    """

    #  Populate the dictionary with object meta data 
    obj_dict = {
    "__class__": obj.__class__.__name__,
    "__module__": obj.__module__
    }

    #  Populate the dictionary with object properties
    obj_dict.update(obj.__dict__)

    return obj_dict

#--------------------------------------------------------------------------------------------------
def dict_to_obj(our_dict):
    """
    Function that takes in a dict and returns a custom object associated with the dict.
    This function makes use of the "__module__" and "__class__" metadata in the dictionary
    to know which object type to create.
    """
    if "py/object" in our_dict: # we used this keyword like in jsonpickle
        fqn = our_dict.pop("py/object")
        ar = fqn.split(".")
        class_name = ar.pop()
        module_name = ".".join(ar)
        module = __import__(module_name)
        class_ = getattr(module,class_name)
        obj = class_(**our_dict)
    elif "__class__" in our_dict:
        # Pop ensures we remove metadata from the dict to leave only the instance arguments
        class_name = our_dict.pop("__class__")
        # Get the module name from the dict and import it
        module_name = our_dict.pop("__module__")
        # We use the built in __import__ function since the module name is not yet known at runtime
        module = __import__(module_name)
        # Get the class from the module
        class_ = getattr(module,class_name)
        # Use dictionary unpacking to initialize the object
        obj = class_(**our_dict)
    else:
        obj = our_dict
    return obj

#--------------------------------------------------------------------------------------------------
def convert_with_custom_func_to_json(obj):
    if hasattr(obj, "to_json"):
        return obj.to_json()
    else:
        return json.JSONEncoder.default(obj) # raise exception!


#--------------------------------------------------------------------------------------------------
class JsonableObject(object):
    def to_json(self):
        d = { "py/object": str(self.__module__) + "." + str(type(self).__qualname__) }
        return d
    def from_json(self):
        pass


#--------------------------------------------------------------------------------------------------
class ObjectJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if inspect.isclass(obj):
            if hasattr(obj, "to_json"):
                #return json.JSONEncoder.default(self, obj.to_json())
                return obj.to_json()
        return json.JSONEncoder.default(obj)

        #     else:
        #         # make the class a dict
        #         d = {
        #                 "__class__": obj.__class__.__name__,
        #                 "__module__": obj.__module__
        #             }
        #         d.update(obj.__dict__) # Populate the dictionary with object properties
        #         return self.default(d)
        # elif hasattr(obj, "__dict__"):
        #     d = dict(
        #         (key, value)
        #         for key, value in inspect.getmembers(obj)
        #         if not key.startswith("__")
        #         and not inspect.isabstract(value)
        #         and not inspect.isbuiltin(value)
        #         and not inspect.isfunction(value)
        #         and not inspect.isgenerator(value)
        #         and not inspect.isgeneratorfunction(value)
        #         and not inspect.ismethod(value)
        #         and not inspect.ismethoddescriptor(value)
        #         and not inspect.isroutine(value)
        #     )
        #     return d

        # return obj

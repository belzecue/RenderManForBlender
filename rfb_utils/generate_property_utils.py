from ..rman_constants import RFB_ARRAYS_MAX_LEN, __RMAN_EMPTY_STRING__, __RESERVED_BLENDER_NAMES__
from ..rfb_logger import rfb_log
from collections import OrderedDict
from bpy.props import *
from copy import deepcopy
import bpy
import sys

def generate_array_property(node, prop_names, prop_meta, node_desc_param, update_array_size_func=None, update_array_elem_func=None):
    '''Generate the necessary properties for an array parameter and
    add it to the node

    Arguments:
        node (ShadingNode) - shading node
        prop_names (list) - the current list of property names for the shading node
        prop_meta (dict) - dictionary of the meta data for the properties for the node
        node_desc_param (NodeDescParam) - NodeDescParam object
        update_array_size_func (FunctionType) - callback function for when array size changes
        update_array_elem_func (FunctionType) - callback function for when an array element changes

    Returns:
        bool - True if succeeded. False if not.
    
    '''  
    def is_array(ndp):          
        ''' A simple function to check if we indeed need to handle this parameter or should just ignore
        it. Color and float ramps are handled generate_property()
        '''
        haswidget = hasattr(ndp, 'widget')
        if haswidget:
            if ndp.widget.lower() in ['null', 'colorramp', 'floatramp']:
                return False

        if hasattr(ndp, 'options'):
            for k,v in ndp.options.items():
                if k in ['colorramp', 'floatramp']:
                    return False

        return True

    if not is_array(node_desc_param):
        return False

    param_name = node_desc_param._name
    param_label = getattr(node_desc_param, 'label', param_name)
    prop_meta[param_name] = {'renderman_type': 'array', 
                            'renderman_array_type': node_desc_param.type,
                            'renderman_name':  param_name,
                            'label': param_label,
                            'type': node_desc_param.type
                            }
    prop_names.append(param_name)
    ui_label = "%s_uio" % param_name
    node.__annotations__[ui_label] = BoolProperty(name=ui_label, default=False)
    sub_prop_names = []
    arraylen_nm = '%s_arraylen' % param_name
    prop = IntProperty(name=arraylen_nm, 
                        default=0, soft_min=0, soft_max=RFB_ARRAYS_MAX_LEN,
                        description="Size of array",
                        update=update_array_size_func)
    node.__annotations__[arraylen_nm] = prop  

    for i in range(0, RFB_ARRAYS_MAX_LEN+1):
        ndp = deepcopy(node_desc_param)
        ndp._name = '%s[%d]' % (param_name, i)
        if hasattr(ndp, 'label'):
            ndp.label = '%s[%d]' % (ndp.label, i)
        #ndp.size = None
        ndp.connectable = True
        ndp.widget = ''
        name, meta, prop = generate_property(node, ndp, update_function=update_array_elem_func)
        meta['renderman_array_name'] = param_name
        sub_prop_names.append(ndp._name)
        prop_meta[ndp._name] = meta
        node.__annotations__[ndp._name] = prop  
            
    setattr(node, param_name, sub_prop_names)   
    return True  

def generate_property(node, sp, update_function=None):
    options = {'ANIMATABLE'}
    param_name = sp._name
    renderman_name = param_name

    # FIXME: figure out a better to skip
    # manifold struct members coming in from OSL shaders
    if 'manifold.' in renderman_name:
        return (None, None, None)

    # blender doesn't like names with __ but we save the
    # "renderman_name with the real one"
    if param_name[0] == '_':
        param_name = param_name[1:]
    if param_name[0] == '_':
        param_name = param_name[1:]

    param_name = __RESERVED_BLENDER_NAMES__.get(param_name, param_name)        

    param_label = sp.label if hasattr(sp,'label') else param_name
    param_widget = sp.widget.lower() if hasattr(sp,'widget') and sp.widget else 'default'
    param_type = sp.type 

    prop_meta = dict()
    param_default = sp.default
    if hasattr(sp, 'vstruct') and sp.vstruct:
        param_type = 'vstruct'
        prop_meta['vstruct'] = True
    else:
        param_type = sp.type
    renderman_type = param_type

    if hasattr(sp, 'vstructmember'):
        prop_meta['vstructmember'] = sp.vstructmember

    if hasattr(sp, 'vstructConditionalExpr'):
        prop_meta['vstructConditionalExpr'] = sp.vstructConditionalExpr        
     
    prop = None

    prop_meta['label'] = param_label
    prop_meta['widget'] = param_widget
    prop_meta['options'] = getattr(sp, 'options', OrderedDict())

    if hasattr(sp, 'connectable') and not sp.connectable:
        prop_meta['__noconnection'] = True

    if isinstance(prop_meta['options'], OrderedDict):
        for k,v in prop_meta['options'].items():
            if k in ['colorramp', 'floatramp']:
                return (None, None, None)

    # set this prop as non connectable
    if param_widget in ['null', 'checkbox', 'switch', 'colorramp', 'floatramp']:
        prop_meta['__noconnection'] = True        


    if hasattr(sp, 'conditionalVisOps'):
        prop_meta['conditionalVisOp'] = sp.conditionalVisOps

    param_help = ''
    if hasattr(sp, 'help'):
        param_help = sp.help

    if hasattr(sp, 'riopt'):
        prop_meta['riopt'] = sp.riopt

    if hasattr(sp, 'riattr'):
        prop_meta['riattr'] = sp.riattr

    if hasattr(sp, 'primvar'):
        prop_meta['primvar'] = sp.primvar

    if hasattr(sp, 'inheritable'):
        prop_meta['inheritable'] = sp.inheritable
    
    if hasattr(sp, 'inherit_true_value'):
        prop_meta['inherit_true_value'] = sp.inherit_true_value

    if hasattr(sp, 'presets'):
        prop_meta['presets'] = sp.presets

    if param_widget == 'colorramp':
        renderman_type = 'colorramp'
        prop = StringProperty(name=param_label, default='')
        rman_ramps = node.__annotations__.get('__COLOR_RAMPS__', [])
        rman_ramps.append(param_name)
        node.__annotations__['__COLOR_RAMPS__'] = rman_ramps     

    elif param_widget == 'floatramp':
        renderman_type = 'floatramp'
        prop = StringProperty(name=param_label, default='')
        rman_ramps = node.__annotations__.get('__FLOAT_RAMPS__', [])
        rman_ramps.append(param_name)
        node.__annotations__['__FLOAT_RAMPS__'] = rman_ramps               

    elif param_type == 'float':
        if sp.is_array():
            prop = FloatProperty(name=param_label,
                                       default=0.0, precision=3,
                                       description=param_help,
                                       update=update_function)       
        else:
            if param_widget in ['checkbox', 'switch']:
                
                prop = BoolProperty(name=param_label,
                                    default=bool(param_default),
                                    description=param_help, update=update_function)
            elif param_widget == 'mapper':
                items = []
                in_items = False
                for k,v in sp.options.items():
                    items.append((str(v), k, ''))
                    if v == param_default:
                        in_items = True
                
                bl_default = ''
                for item in items:
                    if item[0] == str(param_default):
                        bl_default = item[0]
                        break                

                if in_items:
                    prop = EnumProperty(name=param_label,
                                        items=items,
                                        default=bl_default,
                                        description=param_help, update=update_function)
                else:
                    param_min = sp.min if hasattr(sp, 'min') else (-1.0 * sys.float_info.max)
                    param_max = sp.max if hasattr(sp, 'max') else sys.float_info.max
                    param_min = sp.slidermin if hasattr(sp, 'slidermin') else param_min
                    param_max = sp.slidermax if hasattr(sp, 'slidermax') else param_max   

                    prop = FloatProperty(name=param_label,
                                        default=param_default, precision=3,
                                        soft_min=param_min, soft_max=param_max,
                                        description=param_help, update=update_function)

            else:
                param_min = sp.min if hasattr(sp, 'min') else (-1.0 * sys.float_info.max)
                param_max = sp.max if hasattr(sp, 'max') else sys.float_info.max
                param_min = sp.slidermin if hasattr(sp, 'slidermin') else param_min
                param_max = sp.slidermax if hasattr(sp, 'slidermax') else param_max   

                prop = FloatProperty(name=param_label,
                                     default=param_default, precision=3,
                                     soft_min=param_min, soft_max=param_max,
                                     description=param_help, update=update_function)


        renderman_type = 'float'

    elif param_type in ['int', 'integer']:
        if sp.is_array(): 
            prop = IntProperty(name=param_label,
                                default=0,
                                description=param_help, update=update_function)            
        else:
            param_default = int(param_default) if param_default else 0
            # make invertT default 0
            if param_name == 'invertT':
                param_default = 0

            if param_widget in ['checkbox', 'switch']:
                prop = BoolProperty(name=param_label,
                                    default=bool(param_default),
                                    description=param_help, update=update_function)

            elif param_widget == 'mapper':
                items = []
                in_items = False
                for k,v in sp.options.items():
                    v = str(v)
                    if len(v.split(':')) > 1:
                        tokens = v.split(':')
                        v = tokens[1]
                        k = '%s:%s' % (k, tokens[0])
                    items.append((str(v), k, ''))
                    if v == str(param_default):
                        in_items = True
                
                bl_default = ''
                for item in items:
                    if item[0] == str(param_default):
                        bl_default = item[0]
                        break

                if in_items:
                    prop = EnumProperty(name=param_label,
                                        items=items,
                                        default=bl_default,
                                        description=param_help, update=update_function)
                else:
                    param_min = int(sp.min) if hasattr(sp, 'min') else 0
                    param_max = int(sp.max) if hasattr(sp, 'max') else 2 ** 31 - 1

                    prop = IntProperty(name=param_label,
                                    default=param_default,
                                    soft_min=param_min,
                                    soft_max=param_max,
                                    description=param_help, update=update_function)

            else:
                param_min = int(sp.min) if hasattr(sp, 'min') else 0
                param_max = int(sp.max) if hasattr(sp, 'max') else 2 ** 31 - 1

                prop = IntProperty(name=param_label,
                                   default=param_default,
                                   soft_min=param_min,
                                   soft_max=param_max,
                                   description=param_help, update=update_function)
        renderman_type = 'int'

    elif param_type == 'color':
        if sp.is_array():
            prop = FloatVectorProperty(name=param_label,
                                    default=(1.0, 1.0, 1.0), size=3,
                                    subtype="COLOR",
                                    soft_min=0.0, soft_max=1.0,
                                    description=param_help, update=update_function)
        else:
            if param_default == 'null' or param_default is None:
                param_default = (0.0,0.0,0.0)
            prop = FloatVectorProperty(name=param_label,
                                    default=param_default, size=3,
                                    subtype="COLOR",
                                    soft_min=0.0, soft_max=1.0,
                                    description=param_help, update=update_function)
        renderman_type = 'color'
    elif param_type == 'shader':
        param_default = ''
        prop = StringProperty(name=param_label,
                              default=param_default,
                              description=param_help, update=update_function)
        renderman_type = 'string'
    elif param_type in ['string', 'struct', 'vstruct', 'bxdf']:
        if param_default is None:
            param_default = ''
        #else:
        #    param_default = str(param_default)

        if '__' in param_name:
            param_name = param_name[2:]

        if (param_widget in ['fileinput','assetidinput','assetidoutput']):
            prop = StringProperty(name=param_label,
                                  default=param_default, subtype="FILE_PATH",
                                  description=param_help, update=update_function)
        elif param_widget in ['mapper', 'popup']:
            items = []
            
            if param_default == '' or param_default == "''":
                param_default = __RMAN_EMPTY_STRING__

            in_items = False
            for k,v in sp.options.items():
                if v == '' or v == "''":
                    v = __RMAN_EMPTY_STRING__
                items.append((str(v), str(k), ''))         
                if param_default == str(v):
                    in_items = True

            if in_items:
                prop = EnumProperty(name=param_label,
                                    default=param_default, description=param_help,
                                    items=items,
                                    update=update_function)
            else:
                prop = StringProperty(name=param_label,
                                    default=str(param_default),
                                    description=param_help, 
                                    update=update_function)                                        

        elif param_widget == 'scenegraphlocation':
            reference_type = eval(sp.options['nodeType'])
            prop = PointerProperty(name=param_label, 
                        description=param_help,
                        type=reference_type)            

        else:
            prop = StringProperty(name=param_label,
                                default=str(param_default),
                                description=param_help, update=update_function)            
        renderman_type = param_type

    elif param_type in ['vector', 'normal']:
        if param_default is None:
            param_default = '0 0 0'
        prop = FloatVectorProperty(name=param_label,
                                   default=param_default, size=3,
                                   subtype="NONE",
                                   description=param_help, update=update_function)
    elif param_type == 'point':
        if param_default is None:
            param_default = '0 0 0'
        prop = FloatVectorProperty(name=param_label,
                                   default=param_default, size=3,
                                   subtype="XYZ",
                                   description=param_help, update=update_function)
        renderman_type = param_type
    elif param_type == 'int2':
        param_type = 'int'
        is_array = 2
        prop = IntVectorProperty(name=param_label,
                                 default=param_default, size=2,
                                 description=param_help, update=update_function)
        renderman_type = 'int'
        prop_meta['arraySize'] = 2   

    elif param_type == 'float2':
        param_type = 'float'
        is_array = 2
        prop = FloatVectorProperty(name=param_label,
                                 default=param_default, size=2,
                                 description=param_help, update=update_function)
        renderman_type = 'float'
        prop_meta['arraySize'] = 2      

    prop_meta['renderman_type'] = renderman_type
    prop_meta['renderman_name'] = renderman_name
    prop_meta['label'] = param_label
    prop_meta['type'] = param_type

    return (param_name, prop_meta, prop)
# -*- coding: utf-8 -*-
#!/usr/bin/python

import imp, os

def __load_all__(directory="pitfalls"):
    list_modules = os.listdir(directory)
    list_modules.remove('__init__.py')
    all_modules = []
    print (list_modules)
    for module_name in list_modules:
        if module_name.split('.')[-1]=='py':
            module = imp.load_source(module_name, directory+os.sep+module_name)
            all_modules.append(module)
    return all_modules
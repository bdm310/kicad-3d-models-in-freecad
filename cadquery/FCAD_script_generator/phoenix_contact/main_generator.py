# -*- coding: utf8 -*-
#!/usr/bin/python
#
# This was originaly derived from a cadquery script for generating PDIP models in X3D format
# from https://bitbucket.org/hyOzd/freecad-macros
# author hyOzd
#
# Adapted by easyw for step and vrlm export
# See https://github.com/easyw/kicad-3d-models-in-freecad

## requirements
## cadquery FreeCAD plugin
##   https://github.com/jmwright/cadquery-freecad-module

## to run the script just do: freecad scriptName modelName
## e.g. FreeCAD export_conn_jst_xh.py all

## the script will generate STEP and VRML parametric models
## to be used with kicad StepUp script

#* These are FreeCAD & cadquery tools                                       *
#* to export generated models in STEP & VRML format.                        *
#*                                                                          *
#* cadquery script for generating JST-XH models in STEP AP214               *
#*   Copyright (c) 2016                                                     *
#* Rene Poeschl https://github.com/poeschlr                                 *
#* All trademarks within this guide belong to their legitimate owners.      *
#*                                                                          *
#*   This program is free software; you can redistribute it and/or modify   *
#*   it under the terms of the GNU General Public License (GPL)             *
#*   as published by the Free Software Foundation; either version 2 of      *
#*   the License, or (at your option) any later version.                    *
#*   for detail see the LICENCE text file.                                  *
#*                                                                          *
#*   This program is distributed in the hope that it will be useful,        *
#*   but WITHOUT ANY WARRANTY; without even the implied warranty of         *
#*   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the          *
#*   GNU Library General Public License for more details.                   *
#*                                                                          *
#*   You should have received a copy of the GNU Library General Public      *
#*   License along with this program; if not, write to the Free Software    *
#*   Foundation, Inc.,                                                      *
#*   51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA           *
#*                                                                          *
#****************************************************************************

__title__ = "make 3D models of phoenix contact connectors (MSTB and MC series)."
__author__ = "scripts: maurice and hyOzd; models: poeschlr"
__Comment__ = '''make 3D models of phoenix contact types MSTB and MC.'''

___ver___ = "1.1 12/04/2016"

import sys, os
import datetime
from datetime import datetime
sys.path.append("../_tools")
import exportPartToVRML as expVRML
import shaderColors
import re, fnmatch
import yaml

save_memory = True #reducing memory consuming for all generation params
check_Model = True

# Licence information of the generated models.
#################################################################################################
STR_licAuthor = "Rene Poeschl"
STR_licEmail = "poeschlr@gmail.com"
STR_licOrgSys = ""
STR_licPreProc = ""

LIST_license = ["",]
#################################################################################################

body_color_key = "green body"
body_color = shaderColors.named_colors[body_color_key].getDiffuseInt()
pins_color_key = "metal grey pins"
pins_color = shaderColors.named_colors[pins_color_key].getDiffuseInt()
insert_color_key = "gold pins"
insert_color = shaderColors.named_colors[insert_color_key].getDiffuseInt()
screw_color_key = "metal grey pins"
screw_color = shaderColors.named_colors[screw_color_key].getDiffuseInt()

if FreeCAD.GuiUp:
    from PySide import QtCore, QtGui

#checking requirements
#######################################################################
FreeCAD.Console.PrintMessage("FC Version \r\n")
FreeCAD.Console.PrintMessage(FreeCAD.Version())
FC_majorV=FreeCAD.Version()[0];FC_minorV=FreeCAD.Version()[1]
FreeCAD.Console.PrintMessage('FC Version '+FC_majorV+FC_minorV+'\r\n')

if int(FC_majorV) <= 0:
    if int(FC_minorV) < 15:
        reply = QtGui.QMessageBox.information(None,"Warning! ...","use FreeCAD version >= "+FC_majorV+"."+FC_minorV+"\r\n")


# FreeCAD.Console.PrintMessage(M.all_params_soic)
FreeCAD.Console.PrintMessage(FreeCAD.ConfigGet("AppHomePath")+'Mod/')
file_path_cq=FreeCAD.ConfigGet("AppHomePath")+'Mod/CadQuery'
if os.path.exists(file_path_cq):
    FreeCAD.Console.PrintMessage('CadQuery exists\r\n')
else:
    msg="missing CadQuery Module!\r\n\r\n"
    msg+="https://github.com/jmwright/cadquery-freecad-module/wiki"
    reply = QtGui.QMessageBox.information(None,"Info ...",msg)

#######################################################################
from Gui.Command import *

outdir=os.path.dirname(os.path.realpath(__file__))
sys.path.append(outdir)

# Import cad_tools
#sys.path.append("../")
import cq_cad_tools
# Reload tools
reload(cq_cad_tools)
# Explicitly load all needed functions
from cq_cad_tools import FuseObjs_wColors, GetListOfObjects, restore_Main_Tools,\
 exportSTEP, close_CQ_Example, saveFCdoc, z_RotateObject, multiFuseObjs_wColors,\
 closeCurrentDoc, checkBOP, checkUnion

# Gui.SendMsgToActiveView("Run")
Gui.activateWorkbench("CadQueryWorkbench")
import FreeCADGui as Gui

try:
    close_CQ_Example(App, Gui)
except:
    FreeCAD.Console.PrintMessage("can't close example.")

import cadquery as cq
from math import sqrt
from Helpers import show
from collections import namedtuple
import FreeCAD, Draft, FreeCADGui
import ImportGui
sys.path.append("cq_models")
import conn_phoenix_mstb as MSTB
import conn_phoenix_mc as MC
#import conn_molex_53398 as M2
import step_license as L
import add_license as L

if LIST_license[0]=="":
    LIST_license=L.LIST_int_license
    LIST_license.append("")

def export_one_part(modul, variant, configuration, with_plug=False):
    if not variant in modul.all_params:
        FreeCAD.Console.PrintMessage("Parameters for %s doesn't exist in 'M.all_params', skipping." % variant)
        return

    params = modul.all_params[variant]
    series_params = modul.seriesParams
    series = series_params.series_name

    subseries, connector_style = params.series_name.split('-')
    pitch_mpn = '-{:g}'.format(params.pin_pitch)
    lib_name = configuration['lib_name_format_str'].format(series=series[0], style=series[1], pitch=params.pin_pitch)
    mpn = configuration['mpn_format_string'].format(subseries=subseries, style = connector_style,
        rating=series[1], num_pins=params.num_pins, pitch=pitch_mpn)
    FileName = configuration['fp_name_format_string'].format(man = configuration['manufacturer'],
        series = series[0], mpn = mpn, num_rows = 1,
        num_pins = params.num_pins, pitch = params.pin_pitch,
        orientation = configuration['orientation_str'][1] if params.angled else configuration['orientation_str'][0],
        flanged = configuration['flanged_str'][1] if params.flanged else configuration['flanged_str'][0],
        mount_hole = configuration['mount_hole_str'][1] if params.mount_hole else configuration['mount_hole_str'][0])

    destination_dir=lib_name
    if with_plug:
        destination_dir += "__with_plug"
    destination_dir+=".3dshapes"

    ModelName = variant
    ModelName = ModelName.replace(".","_")
    Newdoc = FreeCAD.newDocument(ModelName)
    App.setActiveDocument(ModelName)
    App.ActiveDocument=App.getDocument(ModelName)
    Gui.ActiveDocument=Gui.getDocument(ModelName)
    #App.setActiveDocument(ModelName)
    #Gui.ActiveDocument=Gui.getDocument(ModelName)
    (pins, body, insert, mount_screw, plug, plug_screws) = modul.generate_part(variant, with_plug)

    color_attr = body_color + (0,)
    show(body, color_attr)

    color_attr = pins_color + (0,)
    show(pins, color_attr)

    if insert is not None:
        color_attr = insert_color + (0,)
        show(insert, color_attr)
    if mount_screw is not None:
        color_attr = screw_color + (0,)
        show(mount_screw, color_attr)
    if plug is not None:
        color_attr = body_color + (0,)
        show(plug, color_attr)

        color_attr = screw_color + (0,)
        show(plug_screws, color_attr)

    doc = FreeCAD.ActiveDocument
    doc.Label=ModelName
    objs=FreeCAD.ActiveDocument.Objects
    FreeCAD.Console.PrintMessage(objs)

    i=0
    objs[i].Label = ModelName + "__body"
    i+=1
    objs[i].Label = ModelName + "__pins"
    i+=1
    if insert is not None:
        objs[i].Label = ModelName + "__thread_insert"
        i+=1
    if mount_screw is not None:
        objs[i].Label = ModelName + "__mount_screw"
        i+=1
    if plug is not None:
        objs[i].Label = ModelName + "__plug"
        i+=1
        objs[i].Label = ModelName + "__plug_screws"
    restore_Main_Tools()

    out_dir=destination_dir
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    used_color_keys = [body_color_key, pins_color_key]
    export_file_name=destination_dir+os.sep+FileName+'.wrl'

    export_objects = []
    i=0
    export_objects.append(expVRML.exportObject(freecad_object = objs[i],
            shape_color=body_color_key,
            face_colors=None))
    i+=1
    export_objects.append(expVRML.exportObject(freecad_object = objs[i],
            shape_color=pins_color_key,
            face_colors=None))
    i+=1
    if insert is not None:
        export_objects.append(expVRML.exportObject(freecad_object = objs[i],
                shape_color=insert_color_key,
                face_colors=None))
        used_color_keys.append(insert_color_key)
        i+=1
    if mount_screw is not None:
        export_objects.append(expVRML.exportObject(freecad_object = objs[i],
                shape_color=screw_color_key,
                face_colors=None))
        used_color_keys.append(screw_color_key)
        i+=1
    if plug is not None:
        export_objects.append(expVRML.exportObject(freecad_object = objs[i],
                shape_color=body_color_key,
                face_colors=None))
        i+=1
        export_objects.append(expVRML.exportObject(freecad_object = objs[i],
                shape_color=screw_color_key,
                face_colors=None))
    scale=1/2.54
    colored_meshes = expVRML.getColoredMesh(Gui, export_objects , scale)
    expVRML.writeVRMLFile(colored_meshes, export_file_name, used_color_keys, LIST_license)

    fusion = multiFuseObjs_wColors(FreeCAD, FreeCADGui,
                     ModelName, objs, keepOriginals=True)

    exportSTEP(doc,FileName,out_dir,fusion)

    step_path = '{dir:s}/{name:s}.step'.format(dir=out_dir, name=FileName)

    L.addLicenseToStep(out_dir, '{:s}.step'.format(FileName), LIST_license,\
        STR_licAuthor, STR_licEmail, STR_licOrgSys, STR_licPreProc)

    FreeCAD.activeDocument().recompute()
    # FreeCADGui.activateWorkbench("PartWorkbench")
    if save_memory == False and check_Model==False:
        Gui.SendMsgToActiveView("ViewFit")
        Gui.activeDocument().activeView().viewAxometric()


    # Save the doc in Native FC format
    saveFCdoc(App, Gui, doc, FileName, out_dir)
    if save_memory == True or check_Model==True:
        closeCurrentDoc(ModelName)


    if check_Model==True:
        #ImportGui.insert(step_path,ModelName)

        ImportGui.open(step_path)
        docu = FreeCAD.ActiveDocument
        docu.Label=ModelName

        if checkUnion(docu) == True:
            FreeCAD.Console.PrintMessage('step file is correctly Unioned\n')
        else:
            FreeCAD.Console.PrintError('step file is NOT Unioned\n')
            stop
        FC_majorV=int(FreeCAD.Version()[0])
        FC_minorV=int(FreeCAD.Version()[1])
        if FC_majorV == 0 and FC_minorV >= 17:
            for o in docu.Objects:
                if hasattr(o,'Shape'):
                    chks=checkBOP(o.Shape)
                    #print 'chks ',chks
                    if chks != True:
                        #msg='shape \''+o.Name+'\' \''+ mk_string(o.Label)+'\' is INVALID!\n'
                        msg = 'shape "{name:s}" "{label:s}" is INVALID'.format(name=o.Name, label=o.Label)
                        FreeCAD.Console.PrintError(msg)
                        FreeCAD.Console.PrintWarning(chks[0])
                        stop
                    else:
                        #msg='shape \''+o.Name+'\' \''+ mk_string(o.Label)+'\' is valid\n'
                        msg = 'shape "{name:s}" "{label:s}" is valid'.format(name=o.Name, label=o.Label)
                        FreeCAD.Console.PrintMessage(msg)
        else:
            FreeCAD.Console.PrintError('BOP check requires FC 0.17+\n')

        if save_memory == True:
            saveFCdoc(App, Gui, docu, 'temp', out_dir)
            docu = FreeCAD.ActiveDocument
            closeCurrentDoc(docu.Label)
    return out_dir

class argparse():
    def __init__(self):
        self.config = 'config_phoenix_KLCv3.0.yaml'
        self.model_filter = '*'
        self.series = ['mc','mstb']
        self.with_plug = False

    def parse_args(self, args):
        for arg in args:
            if '=' in arg:
                self.parseValueArg(*arg.split('='))
            else:
                self.argSwitchArg(arg)

    def parseValueArg(self, name, value):
        if name == 'config':
            self.config = value
        elif name == 'model_filter':
            self.model_filter = value
        elif name == 'series':
            self.series = value.split(',')

    def argSwitchArg(self, name):
        if name == '?':
            self.print_usage()
        elif name == 'with_plug':
            self.with_plug = True
        elif name == 'disable_check':
            global check_Model
            check_Model = False
        elif name == 'disable_Memory_reduction':
            global save_memory
            save_memory = False

    def print_usage(self):
        print("Generater script for phoenix contact 3d models.")
        print('usage: FreeCAD export_conn_phoenix.py [optional arguments]')
        print('optional arguments:')
        print('\tconfig=[config file]: default:config_phoenix_KLCv3.0.yaml')
        print('\tmodel_filter=[filter using linux file filter syntax]')
        print('\tseries=[series name],[series name],...')
    def __str__(self):
        return 'config:{:s}, filter:{:s}, series:{:s}, with_plug:{:d}'.format(
            self.config, self.model_filter, str(self.series), self.with_plug)

if __name__ == "__main__" or __name__ == "main_generator":

    FreeCAD.Console.PrintMessage('\r\nRunning...\r\n')

    series_to_build = []
    modelfilter = ""
    with_plug = False

    args = argparse()
    args.parse_args(sys.argv)

    with open(args.config, 'r') as config_stream:
        try:
            configuration = yaml.load(config_stream)
        except yaml.YAMLError as exc:
            print(exc)

    series_to_build = map(str.lower, args.series)
    print(args)
    modelfilter = args.model_filter

    series = []
    if 'mc' in series_to_build:
        series += [MC]
    if 'mstb' in series_to_build:
        series += [MSTB]

    model_filter_regobj=re.compile(fnmatch.translate(modelfilter))
    print("########################################")

    print(args.model_filter)
    for typ in series:
        for variant in typ.all_params.keys():
            if model_filter_regobj.match(variant):
                FreeCAD.Console.PrintMessage('\r\n'+variant+'\r\n')
                out_dir = export_one_part(typ, variant, configuration, with_plug)
        if save_memory == True:
            os.remove('{}/temp.FCStd'.format(out_dir))

    FreeCAD.Console.PrintMessage('\r\nDone\r\n')

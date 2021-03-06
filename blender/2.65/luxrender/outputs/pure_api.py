# -*- coding: utf8 -*-
#
# ***** BEGIN GPL LICENSE BLOCK *****
#
# --------------------------------------------------------------------------
# Blender 2.5 LuxRender Add-On
# --------------------------------------------------------------------------
#
# Authors:
# Doug Hammond
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.
#
# ***** END GPL LICENCE BLOCK *****
#
from ..outputs import LuxLog
import shutil
import tempfile
import os
import platform

if not 'PYLUX_AVAILABLE' in locals():
	# If pylux is not available, revert to 0.8 feature set
	LUXRENDER_VERSION = '0.8'
	
	try:
		if platform.system() == 'Windows':
			# On Windows, shared libraries cannot be overwritten
			# while loaded.
			# In order to facilitate in-place updates on Windows, 
			# copy pylux to temp directory and load from there
			import sys
			orig_sys_path = sys.path
			try:
				sdir = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..'))
				sname = os.path.join(sdir, 'pylux.pyd')
				
				tdir = os.path.abspath(os.path.join(os.path.realpath(tempfile.gettempdir()), 'luxblend25'))
				tname = os.path.join(tdir, 'pylux.pyd')
				
				if not os.path.isdir(tdir):
					os.mkdir(tdir)
				
				import filecmp
				# Check if temp module is up to date, in case multiple copies of Blender
				# is launched. May still fail if launched in too quick succession but better
				# than nothing. Also avoids redundant copy.
				if not (os.path.isfile(tname) and filecmp.cmp(sname, tname, shallow=False)):
					LuxLog('Updating dynamic pylux module')
					# files are not equal, if copy fails then fall back
					shutil.copyfile(sname, tname)
				
				# override sys.path for module loading
				sys.path.insert(0, tdir)
				
				import pylux
				LuxLog('Using dynamic pylux module')
				
			except Exception as e:
				LuxLog('Error loading dynamic pylux module: %s' % str(e))
				LuxLog('Falling back to regular pylux module')
				sys.path = orig_sys_path
				from .. import pylux
				
			# reset sys.path (safer here than in try block)
			sys.path = orig_sys_path
		else:
			from .. import pylux
		
		LUXRENDER_VERSION = pylux.version()
		
		class Custom_Context(pylux.Context):
			'''
			This is the 'pure' entry point to the pylux.Context API
			
			Some methods in this class have been overridden with
			extensions to provide additional functionality in other
			API types (eg. file_api).
			
			The other Custom_Context APIs are based on this one
			'''
			
			PYLUX = pylux
			API_TYPE = 'PURE'
			
			def attributeBegin(self, comment='', file=None):
				'''
				Added for compatibility with file_api
				'''
				
				pylux.Context.attributeBegin(self)
			
			def transformBegin(self, comment='', file=None):
				'''
				Added for compatibility with file_api
				'''
				
				pylux.Context.transformBegin(self)
			
			def logVerbosity(self, verbosity):
				'''
				verbose, default, quiet, very-quiet
				'''
				try:
					filterMap = {
						'verbose': pylux.ErrorSeverity.LUX_DEBUG, 
						'default': pylux.ErrorSeverity.LUX_INFO, 
						'quiet': pylux.ErrorSeverity.LUX_WARNING, 
						'very-quiet': pylux.ErrorSeverity.LUX_ERROR,
						}
					
					pylux.errorFilter(filterMap[verbosity])
				except ValueError:
					pass
				# backwards compatibility
				except NameError:
					pass
				except AttributeError:
					pass
		
		# Backwards-compatibility Context method substitution
		if LUXRENDER_VERSION < '0.8':
			from extensions_framework.util import format_elapsed_time
			
			def printableStatistics(self, add_total):
				stats_dict = {
					'secElapsed': 0.0,
					'samplesSec': 0.0,
					'samplesTotSec': 0.0,
					'samplesPx': 0.0,
					'efficiency': 0.0,
				}
				stats_format = {
					'secElapsed':		format_elapsed_time,
					'samplesSec':		lambda x: 'Samples/Sec: %0.2f'%x,
					'samplesTotSec':	lambda x: 'Total Samples/Sec: %0.2f'%x,
					'samplesPx':		lambda x: 'Samples/Px: %0.2f'%x,
					'efficiency':		lambda x: 'Efficiency: %0.2f %%'%x,
				}
				for k in stats_dict.keys():
					stats_dict[k] = self.statistics(k)
				
					stats_string = ' | '.join(['%s'%stats_format[k](v) for k,v in stats_dict.items()])
					network_servers = self.getServerCount()
					if network_servers > 0:
						stats_string += ' | %i Network Servers Active' % network_servers
				
				return stats_string
			
			Custom_Context.printableStatistics = printableStatistics
			
			Custom_Context.setAttribute = Custom_Context.setOption
			Custom_Context.getAttribute = Custom_Context.getOption
			
			def getRenderingServersStatus(self):
				server_list = []
				for i in range(self.getServerCount()):
					rsi = pylux.RenderingServerInfo()
					pylux.Context.getRenderingServersStatus(self, rsi, i+1)
					server_list.append(rsi)
				return server_list
			Custom_Context.getRenderingServersStatus = getRenderingServersStatus
			
			def saveEXR(self, filename, useHalfFloat, includeZBuffer, tonemapped):
				pass # can't do anything
			Custom_Context.saveEXR = saveEXR
			
			def portalInstance(self, name):
				LuxLog('WARNING: Exporting PortalInstance as ObjectInstance; Portal will not be effective')
				self.objectInstance(name)
			Custom_Context.portalInstace = portalInstance
		
		PYLUX_AVAILABLE = True
		LuxLog('Using pylux version %s' % LUXRENDER_VERSION)
		
	except ImportError as err:
		LuxLog('WARNING: Binary pylux module not available! Visit http://www.luxrender.net/ to obtain one for your system.')
		LuxLog(' (ImportError was: %s)' % err)
		PYLUX_AVAILABLE = False

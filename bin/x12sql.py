#! /usr/bin/env /usr/local/bin/python
# script to validate a X12N batch transaction set  and convert it into an XML document
#
#    $Id$
#    This file is part of the pyX12 project.
#
#    Copyright (c) 2001-2004 Kalamazoo Community Mental Health Services,
#                John Holland <jholland@kazoocmh.org> <john@zoner.org>
#
#    All rights reserved.
#
#        Redistribution and use in source and binary forms, with or without modification, 
#        are permitted provided that the following conditions are met:
#
#        1. Redistributions of source code must retain the above copyright notice, this list 
#           of conditions and the following disclaimer. 
#        
#        2. Redistributions in binary form must reproduce the above copyright notice, this 
#           list of conditions and the following disclaimer in the documentation and/or other 
#           materials provided with the distribution. 
#        
#        3. The name of the author may not be used to endorse or promote products derived 
#           from this software without specific prior written permission. 
#
#        THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS'' AND ANY EXPRESS OR IMPLIED 
#        WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF 
#        MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO 
#        EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, 
#        EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT 
#        OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS 
#        INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN 
#        CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) 
#        ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF 
#        THE POSSIBILITY OF SUCH DAMAGE.

"""
Generate SQL DDL for a table structure fitting a map
"""

import os, os.path
import sys
import logging
from types import *
import pdb
#import profile
import tempfile

# Intrapackage imports
import pyx12
import pyx12.map_if
import pyx12.x12n_document
import pyx12.params

__author__  = pyx12.__author__
__status__  = pyx12.__status__
__version__ = pyx12.__version__
__date__    = pyx12.__date__

TRANS_PRE = 't_'

def format_name(name):
    return name.replace(' ', '_')
    
def gen_sql(map_root):
    """
    iterate through map, generate sql
    """
    fd = sys.stdout
    tbl_stack = []
    in_table = False
    for node in map_root:
        if node.id is None:
            continue
        id = node.id
        if id[:3] in ('ISA', 'IEA', 'TA1') or \
            id[:2] in ('GS', 'GE', 'SE'):
            continue
        if node.is_map_root():
            continue
        if node.is_loop():
            if in_table:
                fd.write(') ON [PRIMARY]\nGO\n\n')
                del tbl_stack[-1]
            table_name = '%sloop_%s_%s' % (TRANS_PRE, node.id, format_name(node.name))
            pk = '%s_num' % (node.id)
            fd.write('CREATE TABLE [%s] ( -- %s\n' % (table_name, node.get_path()))
            tbl_stack.append((table_name, pk))
            in_table = True
            fd.write('\t[%s] [int] IDENTITY (1, 1) NOT NULL\n' % (pk))
        elif node.is_segment():
            #if node.get_max_repeat() != 1:
            if node.get_max_repeat() != 1 or not in_table:
                if in_table:
                    fd.write(') ON [PRIMARY]\nGO\n\n')
                    del tbl_stack[-1]
                table_name = '%s%s_%s' % (TRANS_PRE, node.id, format_name(node.name))
                pk = '%s_num' % (node.id)
                fd.write('CREATE TABLE [%s] ( -- %s\n' % (table_name, node.get_path()))
                in_table = True
                tbl_stack.append((table_name, pk))
                fd.write('\t[%s] [int] IDENTITY (1, 1) NOT NULL\n' % (pk))
        elif node.is_element():
            fd.write(',\t[%s_%s]' % (node.id, format_name(node.name)))
            if node.data_type in ('DT', 'TM'):
                fd.write(' [datetime]')
            elif node.data_type in ('AN', 'ID'):
                if node.min_len == node.max_len:
                    fd.write(' [char] (%s)' % (node.max_len))
                else:
                    fd.write(' [varchar] (%s)' % (node.max_len))
            elif node.data_type == 'N0':
                fd.write(' [int]')
            elif node.data_type == 'R' or node.data_type[0] == 'N':
                fd.write(' [float]')
            fd.write(' NULL')
            fd.write('  -- %s(%s, %s)' % (node.data_type, node.min_len, node.max_len))
            fd.write('\n')
        elif node.is_composite():
            pass
    return None

   
def usage():
    sys.stdout.write('x12sql.py %s (%s)\n' % (__version__, __date__))
    sys.stdout.write('usage: x12sql.py [options] source_files\n')
    sys.stdout.write('\noptions:\n')
    sys.stdout.write('  -m <path>  Path to map files\n')
    sys.stdout.write('  -p <path>  Path to to pickle files\n')
    sys.stdout.write('  -q         Quiet output\n')
    sys.stdout.write('  -v         Verbose output\n')
    
def main():
    """
    Set up environment for processing
    """
    import getopt
    param = pyx12.params.params()
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'c:fm:p:qv')
    except getopt.error, msg:
        usage()
        sys.exit(2)
    logger = logging.getLogger('pyx12')
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(module)s %(lineno)d %(message)s')

    stderr_hdlr = logging.StreamHandler()
    stderr_hdlr.setFormatter(formatter)
    logger.addHandler(stderr_hdlr)

    #param.set_param('map_path', os.path.expanduser('/usr/local/share/pyx12/map'))
    #param.set_param('pickle_path', os.path.expanduser('/tmp'))
    for o, a in opts:
        if o == '-v': logger.setLevel(logging.DEBUG)
        if o == '-q': logger.setLevel(logging.ERROR)
        if o == '-f': param.set_param('force_map_load', True)
        if o == '-m': param.set_param('map_path', a)
        if o == '-p': param.set_param('pickle_path', a)
        if o == '-l':
            try:
                hdlr = logging.FileHandler(a)
                hdlr.setFormatter(formatter)
                logger.addHandler(hdlr) 
            except IOError:
                logger.error('Could not open log file: %s' % (a))
        #if o == '-9': target_997 = os.path.splitext(src_filename)[0] + '.997'
    map_path = param.get_param('map_path')

    for map_filename in args:
        try:
            gen_sql(pyx12.map_if.map_if(os.path.join(map_path, map_filename), param))
        except IOError:
            logger.error('Could not open files')
            usage()
            sys.exit(2)
        except KeyboardInterrupt:
            print "\n[interrupt]"

    return True

#profile.run('x12n_document(src_filename)', 'pyx12.prof')
if __name__ == '__main__':
    sys.exit(not main())

    def pop_to_parent_loop(self, node):
        if node.is_map_root():
            return node
        map_node = node.parent
        if map_node is None:
            raise EngineError, "Node is None: %s" % (node.name)
        while not (map_node.is_loop() or map_node.is_map_root()): 
            map_node = map_node.parent
        if not (map_node.is_loop() or map_node.is_map_root()):
            raise EngineError, "Called pop_to_parent_loop, can't find parent loop"
        return map_node
        


#! /usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2020 Francis Laniel <francis.laniel@lip6.fr>
"""This python script extracts layers from SVG pictures designed by inkscape and
export them to PDF so they can be used in beamer to do animation.
It is based on an original idea and script of Julien Sopena
<julien.sopena@lip6.fr>.

This script does not just extract dumbly the layer but create new pictures from
layers.
To extract the layers, they have to be named "label-figX" where X must respect
the Beamer overlay specification (http://tug.ctan.org/macros/latex/contrib/beamer/doc/beameruserguide.pdf Section 3.10):
* A number, like 2, this layer will only be visible in corresponding
picture, here picture 2.
* A list of number, like [2,3,5], this layer will only be visible in listed
pictures, here pictures 2, 3 and 5.
* An interval, multiple cases are possible:
	* A conventional one, like [2-5], this layer will only be visible in all
	pictures inside the interval, here pictures 2 to 5 included.
	* A no lower bound interval, like [-6], the layer will only be visible in
	pictures to upper bound, here pictures 1 to 6.
	* A no upper bound interval, like [3-], the layer will be visible in all
	pictures from the lower bound, here pictures 3 until last one.
* A mix of list and interval, like [-3,4,5-6,8-], in the example the layer will
be visible on all pictures expect the 7th.
"""
import argparse
from shutil import which
import sys
import xml.etree.ElementTree as ET
import subprocess
import os
import re
import traceback
import copy

# Inkscape program name.
INKSCAPE = 'inkscape'

# Inkscape options that this script uses.
# See inkscape manual for more information.
SHELL_OPTION = '--shell'
AREA_DRAWING_OPTION = '--export-area-drawing'
WITHOUT_GUI_OPTION = '--without-gui'
EXPORT_PDF_OPTION = '--export-pdf'

# To exit inkscape shell just type 'quit'.
QUIT = 'quit\n'

PDF_EXTENSION = '.pdf'

# I found theses XML namespaces into a file created with inkscape.
# They will be used to find SVG elements.
NAMESPACES = {
	'dc': "http://purl.org/dc/elements/1.1/",
	'cc': "http://creativecommons.org/ns#",
	'rdf': "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
	'svg': "http://www.w3.org/2000/svg",
	'xlink': "http://www.w3.org/1999/xlink",
	'sodipodi': "http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd",
	'inkscape': "http://www.inkscape.org/namespaces/inkscape"
}

# Inkscape mark layer with the following attributes
LAYER = "inkscape:groupmode='layer'"

# We search g elements defined in svg namespace which are used as layers.
SEARCH_LAYER = 'svg:g[@{}]'.format(LAYER)

# Label are defined by inkscape namespace.
# So its key has this namespace.
LABEL_KEY = '{{{}}}label'.format(NAMESPACES['inkscape'])

# The style of a <g> SVG element contains multiple informations.
STYLE = 'style'

# It, among others, contains if the <g> is visible or not.
# The following value set it visible.
VISIBLE = 'display:inline'

def vprint(verbose, *argv):
	"""Print only if verbose is true.
	:param verbose: A boolean which is used to print if true.
	:type verbose: bool.
	:param *argv: The data to print, it must correpond to argument expected by
	print.
	:type *argv:
	"""
	if verbose:
		print(*argv)

def get_label_max_fig_number(label):
	"""Parse the label of a layer to extract its higher figure number.
	:param label: The label of the current layer.
	:type label: str.
	:returns: The level of the current layer, or 0 if it does not have a level.
	:rtype: int.
	"""
	# This regex matches the following:
	# * figX
	# * fig[X,Y,...] (note that maybe X > Y)
	# * fig[X-Y]
	# * fig[X-]
	# * fig[-X]
	# * fig[U,V,-W,X-,Y-Z]
	# The result will be contained in match.group(1) if the regex matched.
	match = re.search('fig\[?([^\]]+)\]?', label, re.IGNORECASE)

	if not match:
		return 0

	# As stated above, fig_number can be a lot of thing.
	# re.split('[,-]') permits getting all the number inside the interval
	# If there is no interval, the list returned by this function contains only
	# one number.
	numbers = re.split('[-,]', match.group(1))

	# First we remove potential empty strings.
	# Indeed, if user gave [1-], numbers = ['1', ''].
	# The empty string will fail the conversion to int.
	numbers = list(filter(len, numbers))

	try:
		# We can now convert string to int.
		# If there is an error now, this is a "chair-keyboard" one.
		numbers = list(map(int, numbers))
	except ValueError as ve:
		sys.exit('The figure label is malformed: {}.\nUse --help option to see how to format them.\nThe received exception was:\n{}'.format(label, traceback.format_exc()))

	# Finally, we return the max of these int.
	return max(numbers)

def get_last_figure_number(root):
	"""Get and return the higher figure number.

	In an SVG figure with 3 layers named like this:
	* layer_fig1
	* layer_fig[2,3]
	* layer_fig[1-]
	The higher figure number is 3.

	:param root: The SVG root.
	:type root: TODO
	:returns: The higher figure number.
	:rtype: int.
	"""
	last_number = 0

	for group in root.findall(SEARCH_LAYER, namespaces = NAMESPACES):
		# Once we get the label of the layer, we parse it to extract its higher
		# number.
		# Inkscape use <g> element for layer.
		# NOTE <g> elements are used to group other SVG elements.
		number = get_label_max_fig_number(group.attrib[LABEL_KEY])

		if number > last_number:
			last_number = number

	return last_number

def include_number(label, number, last_number):
	"""A layer will be included if its label contains number.

	For example, if number is 3 and label is:
	* layer_fig1, the layer will not be included.
	* layer_fig[3,4], the layer will be included.
	* layer_fig[1-3], the layer will be included.
	* layer_fig[-2], the layer will not be included.
	* layer_fig[1-], the layer will be included.

	:param label: The label of the layer to analyse.
	:type label: str.
	:param number: The current number of the figure.
	:type number: int.
	:param last_number: The last number of the figure.
	:type last_number: int.
	:returns: True if this layer needs to be displayed, false otherwise.
	:rtype: bool
	"""
	# Get X which follows figX.
	match = re.search('fig\[?([^\]]+)\]?', label, re.IGNORECASE)

	if not match:
		return False

	# Now deal with the match!
	# Match can be a lot of thing, so I do not have any idea of how to name this
	# variable...
	# NOTE if the match does not contain ',' re.split returns the match.
	for x in match.group(1).split(','):
		submatch = re.search('(\d+)?(-?)(\d+)?', x)

		if not submatch:
			print("I have good reasons to think your layer's label is badly formatted, see if '{}' respects the naming rules (use script with --help)\nI will ignore this and try to produce the figures anyway.".format(x), file = sys.stderr)

			continue

		# If submatch.group(1) is None, there is an high probability that we are
		# dealing with an '-X' interval.
		# So, we use submatch.group(2) as first_match.
		if submatch.group(1):
			first_match = submatch.group(1)
		else:
			first_match = submatch.group(2)

		# Initialize these variable here, they will be set below?
		first = 0
		last = 0

		# If first_match is a '-', we are dealing with '-X'
		if first_match == '-':
			first = 1

			if not submatch.group(3):
				print("I have good reasons to think your layer's label is badly formatted, see if '{}' respects the naming rules (use script with --help)\nI will ignore this and try to produce the figures anyway.".format(x), file = sys.stderr)

				continue

			last = int(submatch.group(3))
		else: # if first_match is an int, it can be 'X', 'X-' or 'X-Y'
			first = int(first_match)

			# The submatch is just 'X'.
			if not submatch.group(2):
				last = first
			elif submatch.group(2) == '-': # The submatch is an interval.
				# The submatch is an 'X-Y' interval
				if submatch.group(3):
					last = int(submatch.group(3))
				else: # The submatch is an 'X-' interval.
					last = last_number

		if first <= number and number <= last:
			return True

	return False

def set_visible(group):
	"""Make a <g> SVG element visible
	:param group: The <g> element which will be visible.
	:type group: TODO
	"""
	group.set(STYLE, VISIBLE)

def remove(root, group):
	"""Remove a <g> SVG element from the file.
	:param root: The root of SVG file.
	:type root: TODO.
	:param group: The group to remove.
	:type group: TODO.
	"""
	root.remove(group)

def name_without_extension(filename):
	"""Remove the extension of a filename.
	:param filename: The filename whom extension has to be removed.
	:type filename: str.
	:return: The filename without its extension.
	:rtype: str.
	"""
	return os.path.splitext(filename)[0]

def create_svgs(svg_filename, tree, root, last_number):
	"""Create SVG files for each figure.

	For example, if the figure contains layers labeled like this:
	* layer_fig1
	* layer_fig[2,3]
	* layer_fig[1-]
	There will be 3 SVG files:
	* svg_fig1.svg
	* svg_fig2.svg
	* svg_fig3.svg
	More generally, there will be last_number SVG files.

	:param svg_filename: Name of the SVG file given by user.
	:type svg_filename: str.
	:param tree: The XML tree of the SVG file given by user.
	:type tree: TODO.
	:param root: The XML root of the SVG file given by user.
	:type root: TODO
	:param last_number: The higher number.
	:param last_number: int.
	:returns: A list of SVG filenames ready to be converted by inkscape.
	:rtype: list<str>
	"""
	svgs = []

	# First, get all the layers.
	groups = root.findall(SEARCH_LAYER, namespaces = NAMESPACES)

	# Process layers in [1, last_number]
	for number in range(1, last_number + 1):
		# Since we will modify the root each iteration we need to locally copy it
		# so we operate on its copy only.
		# TODO We can read the file at each iteration but I think this is faster to
		# just copy the memory instead of reading a file.
		# For this kind of question, the best answer is to test and profile the
		# code.
		processed_root = copy.copy(root)

		for group in groups:
			if include_number(group.attrib[LABEL_KEY], number, last_number):
				set_visible(group)
			else:
				# Instead of setting it invisible I prefer to remove it.
				# This will make the generated SVG file lighter and so inkscape will
				# convert it faster.
				remove(processed_root, group)

		# Create svg filename.
		temp_file = '{}-fig{}.svg'.format(os.path.basename(name_without_extension(svg_filename)), number)

		# Add it to returned list.
		svgs.append(temp_file)

		# Set the modified root as the root tree.
		tree._setroot(processed_root)

		# Write the XML tree in this file.
		tree.write(temp_file)

	# Restore the original root.
	tree._setroot(root)

	return svgs

def name_to_pdf(filename):
	"""Replace filename extension with 'pdf'.
	:param filename: The filename whom extension has to be replaced.
	:type filename: str.
	:returns: The filename where extension was replaced by 'pdf'
	:rtype: str.
	"""
	return '{}{}'.format(name_without_extension(filename), PDF_EXTENSION)

def create_pdf_filename(destination, svg):
	"""Create a path with complete path and filename for a PDF file.
	:param destination: The destination directory of PDF file
	:type destination: str.
	:param svg: The SVG filename.
	:type svg: str.
	:returns: The complete path and filename for a PDF file.
	:rtype: str.
	"""
	# os.path.basename on name_to_pdf avoid duplicating path in path.
	return '{}/{}'.format(destination, os.path.basename(name_to_pdf(svg)))

def inkscape(svg, destination, no_export_area_drawing):
	"""Call inkscape to export SVG file to PDF
	:param svg: SVG filename.
	:type svg: str.
	:param destination: Output directory of PDF file.
	:type destination: str.
	:param no_export_area_drawing: Export the whole page if true, otherwise only
	the drawing bounding box is exported.
	:type no_export_area_drawing: bool.
	:returns: The code returned by inkscape.
	:rtype: int.
	"""
	# EXPORT_PDF_OPTION of inkscape need a file so we create PDF filename with
	# destination and svg.
	pdf = create_pdf_filename(destination, svg)

	if no_export_area_drawing:
		args = [INKSCAPE, svg, WITHOUT_GUI_OPTION, EXPORT_PDF_OPTION, pdf]
	else:
		args = [INKSCAPE, svg, AREA_DRAWING_OPTION, WITHOUT_GUI_OPTION, EXPORT_PDF_OPTION, pdf]

	return subprocess.run(args).returncode

def start_inkscape():
	"""Start inkscape --shell inside a subprocess.
	:returns: A subprocess corresponding to inkscape --shell.
	:rtype: subprocess.Popen.
	"""
	# Open pipes for stdin, stdout and stderr and set bufsize to 0, so the writes
	# to the pipes are done immediately.
	return subprocess.Popen([INKSCAPE, SHELL_OPTION], bufsize = 0, stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.PIPE)

def convert(inkscape, svg, destination, no_export_area_drawing):
	"""Convert SVG file to PDF by using inkscape subprocess.
	:param inkscape: A subprocess containing inkscape --shell.
	:type inkscape: subprocess.Popen.
	:param svg: SVG filename.
	:type svg: str.
	:param destination: Output directory of PDF file.
	:type destination: str.
	:param no_export_area_drawing: Export the whole page if true, otherwise only
	the drawing bounding box is exported.
	:type no_export_area_drawing: bool.
	:returns: None or inkscape's returncode if the execution failed at some
	moment.
	:rtype: NoneType/int.
	"""
	# EXPORT_PDF_OPTION of inkscape need a file so we create PDF filename with
	# destination and svg.
	pdf = create_pdf_filename(destination, svg)

	if no_export_area_drawing:
		args = "{} {} {} {}\n".format(svg, WITHOUT_GUI_OPTION, EXPORT_PDF_OPTION, pdf)
	else:
		args = "{} {} {} {} {}\n".format(svg, AREA_DRAWING_OPTION, WITHOUT_GUI_OPTION, EXPORT_PDF_OPTION, pdf)

	# Write the command to execute on inkscape stdin.
	inkscape.stdin.write(args.encode())

	# Here, inkscape returncode should be None.
	# If it is an int, there is surely an error.
	return inkscape.returncode

def quit_inkscape(inkscape):
	"""Quit the inkscape --shell wait for its termination and returns its
	returncode.
	:param inkscape: A subprocess containing inkscape --shell.
	:type inkscape: subprocess.Popen.
	:returns: Inkscape's returncode.
	:rtype: int.
	"""
	# Write 'quit' to stdin to quit inkscape's shell.
	inkscape.stdin.write(QUIT.encode())

	# Wait for the termination of inkscape so it converts all the files and
	# returns its returncode.
	return inkscape.wait()

def main():
	"""Execute this script."""
	parser = argparse.ArgumentParser(description = __doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
	parser.add_argument('svg', help = "SVG file to parse.")
	parser.add_argument('-d', '--destination', dest = 'destination', help = 'PDF files will be stored in this directory. This must exist before script execution.')
	parser.add_argument('-n', '--no-export-area-drawing', help = 'Export the whole SVG document and not only drawing bounding box.', action = 'store_true')
	parser.add_argument('-k', '--keep', help = 'Keep intermediate svg files created.', action = 'store_true')
	parser.add_argument('-v', '--verbose', help = 'increase output verbosity',  action = 'store_true')

	args = parser.parse_args()

	# If destination was not given by the user we default it to dirname of SVG
	# file.
	if not args.destination:
		# Use first abspath to avoid getting destination empty if SVG file is in
		# the same directory than this script, see:
		# https://stackoverflow.com/a/7783326
		args.destination = os.path.dirname(os.path.abspath(args.svg))

	# Check if inkscape is installed.
	if not which(INKSCAPE):
		sys.exit('{} must be installed for this script to work correctly.'.format(INKSCAPE))

	# Parse the svg file and get its root.
	tree = ET.parse(args.svg)
	root = tree.getroot()

	last_picture_number = get_last_figure_number(root)

	vprint(args.verbose, "Last number: {}".format(last_picture_number))

	# If last_picture_number is 0, this means the SVG does not contain layer names
	# like "-FigX".
	# So we simply export the SVG as PDF and exit.
	if not last_picture_number:
		sys.exit(inkscape(args.svg, args.destination, args.no_export_area_drawing))

	# Create SVG files corresponding to figures.
	svgs = create_svgs(args.svg, tree, root, last_picture_number)

	inkscape_process = start_inkscape()

	for svg in svgs:
		vprint(args.verbose, "Convert {} to PDF".format(svg))

		ret = convert(inkscape_process, svg, args.destination, args.no_export_area_drawing)

		if ret != None:
			sys.exit('{} returns {} and should not have returned, there is surely an error!'.format(INKSCAPE, ret))

	ret = quit_inkscape(inkscape_process)

	# We can only remove the temporary files once inkscape finished to convert
	# them.
	if not args.keep:
		for svg in svgs:
			os.remove(svg)

	sys.exit(ret)

if __name__ == "__main__":
	main()
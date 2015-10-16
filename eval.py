#!/usr/bin/env python

###################################################################################
# TILE GROUP EXPERIMENTS
###################################################################################

from __future__ import print_function
import os
import subprocess
import argparse
import pprint
import numpy
import sys
import re
import logging
import fnmatch
import string
import argparse
import pylab
import datetime
import math
import time
import fileinput
from lxml import etree

import numpy as np
import matplotlib.pyplot as plot

from matplotlib.font_manager import FontProperties
from matplotlib.ticker import MaxNLocator
from matplotlib.ticker import LogLocator
from matplotlib.ticker import LinearLocator
from pprint import pprint, pformat
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib import rc
from operator import add

import csv
import brewer2mpl
import matplotlib

from options import *
from functools import wraps

###################################################################################
# LOGGING CONFIGURATION
###################################################################################

LOG = logging.getLogger(__name__)
LOG_handler = logging.StreamHandler()
LOG_formatter = logging.Formatter(
    fmt='%(asctime)s [%(funcName)s:%(lineno)03d] %(levelname)-5s: %(message)s',
    datefmt='%m-%d-%Y %H:%M:%S'
)
LOG_handler.setFormatter(LOG_formatter)
LOG.addHandler(LOG_handler)
LOG.setLevel(logging.INFO)

###################################################################################
# OUTPUT CONFIGURATION
###################################################################################

BASE_DIR = os.path.dirname(__file__)
OPT_FONT_NAME = 'Helvetica'
OPT_GRAPH_HEIGHT = 300
OPT_GRAPH_WIDTH = 400

# Make a list by cycling through the colors you care about
# to match the length of your data.

NUM_COLORS = 5
COLOR_MAP = ( '#F58A87', '#80CA86', '#9EC9E9', "#F15854", "#66A26B", "#5DA5DA")


#COLOR_MAP = ('#F15854', '#9C9F84', '#F7DCB4', '#991809', '#5C755E', '#A97D5D')
OPT_COLORS = COLOR_MAP

OPT_GRID_COLOR = 'gray'
OPT_LEGEND_SHADOW = False
OPT_MARKERS = (['o', 's', 'v', "^", "h", "v", ">", "x", "d", "<", "|", "", "|", "_"])
OPT_PATTERNS = ([ "////", "////", "o", "o", "\\\\" , "\\\\" , "//////", "//////", ".", "." , "\\\\\\" , "\\\\\\" ])

OPT_LABEL_WEIGHT = 'bold'
OPT_LINE_COLORS = COLOR_MAP
OPT_LINE_WIDTH = 5.0
OPT_MARKER_SIZE = 8.0
DATA_LABELS = []

OPT_STACK_COLORS = ('#AFAFAF', '#F15854', '#5DA5DA', '#60BD68',  '#B276B2', '#DECF3F', '#F17CB0', '#B2912F', '#FAA43A')

# SET FONT

LABEL_FONT_SIZE = 16
TICK_FONT_SIZE = 14
TINY_FONT_SIZE = 8
LEGEND_FONT_SIZE = 20

AXIS_LINEWIDTH = 1.3
BAR_LINEWIDTH = 1.2


matplotlib.rcParams['ps.useafm'] = True
matplotlib.rcParams['pdf.use14corefonts'] = True
matplotlib.rcParams['text.usetex'] = True
#matplotlib.rcParams['text.latex.preamble']=[r'\usepackage{euler}']

LABEL_FP = FontProperties(family=OPT_FONT_NAME, style='normal', size=LABEL_FONT_SIZE, weight='bold')
TICK_FP = FontProperties(family=OPT_FONT_NAME, style='normal', size=TICK_FONT_SIZE)
TINY_FP = FontProperties(family=OPT_FONT_NAME, style='normal', size=TINY_FONT_SIZE)
LEGEND_FP = FontProperties(family=OPT_FONT_NAME, style='normal', size=LEGEND_FONT_SIZE, weight='bold')

YAXIS_TICKS = 5
YAXIS_ROUND = 1000.0

###################################################################################
# CONFIGURATION
###################################################################################

BASE_DIR = os.path.dirname(os.path.realpath(__file__))

PELOTON_BUILD_DIR = BASE_DIR + "/../peloton/build"
HYADAPT = PELOTON_BUILD_DIR + "/src/hyadapt"
YCSB = PELOTON_BUILD_DIR + "/src/ycsb"

OUTPUT_FILE = "outputfile.summary"

PROJECTIVITY_DIR = BASE_DIR + "/results/projectivity/"
SELECTIVITY_DIR = BASE_DIR + "/results/selectivity/"
OPERATOR_DIR = BASE_DIR + "/results/operator/"
YCSB_DIR = BASE_DIR + "/results/ycsb/"

LAYOUTS = ("row", "column", "hybrid")
OPERATORS = ("direct", "aggregate")

SCALE_FACTOR = 2000.0

SELECTIVITY = (0.2, 0.4, 0.6, 0.8, 1.0)
PROJECTIVITY = (0.1, 0.2, 0.3, 0.4, 0.5)

OP_PROJECTIVITY = (0.1, 1.0)

COLUMN_COUNTS = (50, 200)
WRITE_RATIOS = (0, 0.1)

TRANSACTION_COUNT = 3

PROJECTIVITY_EXPERIMENT = 1
SELECTIVITY_EXPERIMENT = 2
OPERATOR_EXPERIMENT = 3
YCSB_EXPERIMENT = 1

YCSB_SCALE_FACTOR = 100.0
YCSB_TRANSACTION_COUNT = 100

YCSB_OPERATIONS = ["Read", "Scan", "Insert", "Delete", "Update", "RMW"]

###################################################################################
# UTILS
###################################################################################

def chunks(l, n):
    """ Yield successive n-sized chunks from l.
    """
    for i in xrange(0, len(l), n):
        yield l[i:i + n]

def loadDataFile(n_rows, n_cols, path):
    file = open(path, "r")
    reader = csv.reader(file)

    data = [[0 for x in xrange(n_cols)] for y in xrange(n_rows)]

    row_num = 0
    for row in reader:
        column_num = 0
        for col in row:
            data[row_num][column_num] = float(col)
            column_num += 1
        row_num += 1

    return data

def next_power_of_10(n):
    return (10 ** math.ceil(math.log(n, 10)))

def get_upper_bound(n):
    return (math.ceil(n / YAXIS_ROUND) * YAXIS_ROUND)

# # MAKE GRID
def makeGrid(ax):
    axes = ax.get_axes()
    axes.yaxis.grid(True, color=OPT_GRID_COLOR)
    for axis in ['top','bottom','left','right']:
            ax.spines[axis].set_linewidth(AXIS_LINEWIDTH)
    ax.set_axisbelow(True)

# # SAVE GRAPH
def saveGraph(fig, output, width, height):
    size = fig.get_size_inches()
    dpi = fig.get_dpi()
    LOG.debug("Current Size Inches: %s, DPI: %d" % (str(size), dpi))

    new_size = (width / float(dpi), height / float(dpi))
    fig.set_size_inches(new_size)
    new_size = fig.get_size_inches()
    new_dpi = fig.get_dpi()
    LOG.debug("New Size Inches: %s, DPI: %d" % (str(new_size), new_dpi))

    pp = PdfPages(output)
    fig.savefig(pp, format='pdf', bbox_inches='tight')
    pp.close()
    LOG.info("OUTPUT: %s", output)

###################################################################################
# PLOT
###################################################################################

def create_bar_legend():
    fig = pylab.figure()
    ax1 = fig.add_subplot(111)

    figlegend = pylab.figure(figsize=(6, 1.0))

    num_items = len(LAYOUTS);
    ind = np.arange(1)
    margin = 0.10
    width = ((1.0 - 2 * margin) / num_items) * 2

    bars = [None] * len(LAYOUTS) * 2

    for group in xrange(len(LAYOUTS)):
        data = [1]
        bars[group] = ax1.bar(ind + margin + (group * width), data, width,
                              color=OPT_COLORS[group],
                              hatch=OPT_PATTERNS[group * 2],
                              linewidth=BAR_LINEWIDTH)

    LABELS = ["Row", "Column", "Hybrid"]

    # LEGEND
    figlegend.legend(bars, LABELS, prop=LABEL_FP,
                     loc=1, ncol=3,
                     mode="expand", shadow=OPT_LEGEND_SHADOW,
                     frameon=False, borderaxespad=0.0, handleheight=2, handlelength=3.5)

    figlegend.savefig('legend_bar.pdf')

def create_legend():
    fig = pylab.figure()
    ax1 = fig.add_subplot(111)

    figlegend = pylab.figure(figsize=(8, 0.5))
    idx = 0
    lines = [None] * len(LAYOUTS)

    layouts = ("Row", "Column", "Hybrid")

    for group in xrange(len(LAYOUTS)):
        data = [1]
        x_values = [1]

        lines[idx], = ax1.plot(x_values, data, color=OPT_LINE_COLORS[idx], linewidth=OPT_LINE_WIDTH,
                 marker=OPT_MARKERS[idx], markersize=OPT_MARKER_SIZE, label=str(group))

        idx = idx + 1

    # LEGEND
    figlegend.legend(lines,  layouts, prop=LEGEND_FP, loc=1, ncol=4, mode="expand", shadow=OPT_LEGEND_SHADOW,
                     frameon=False, borderaxespad=0.0, handlelength=4)

    figlegend.savefig('legend.pdf')


def create_projectivity_line_chart(datasets):
    fig = plot.figure()
    ax1 = fig.add_subplot(111)

    # X-AXIS
    x_values = PROJECTIVITY
    N = len(x_values)
    x_labels = x_values

    num_items = len(LAYOUTS);
    ind = np.arange(N)
    idx = 0

    YLIMIT = 100

    # GROUP
    for group_index, group in enumerate(LAYOUTS):
        group_data = []

        # LINE
        for line_index, line in enumerate(x_values):
            group_data.append(datasets[group_index][line_index][1])

        LOG.info("%s group_data = %s ", group, str(group_data))

        ax1.plot(x_values, group_data, color=OPT_LINE_COLORS[idx], linewidth=OPT_LINE_WIDTH,
                 marker=OPT_MARKERS[idx], markersize=OPT_MARKER_SIZE, label=str(group))

        idx = idx + 1

    # GRID
    axes = ax1.get_axes()
    makeGrid(ax1)

    # Y-AXIS
    ax1.yaxis.set_major_locator(LinearLocator(YAXIS_TICKS))
    ax1.minorticks_off()
    ax1.set_ylabel("Execution time (ms)", fontproperties=LABEL_FP)
    #ax1.set_yscale('log', basey=2)
    #ax1.set_ylim([YAXIS_MIN, YAXIS_MAX])

    # X-AXIS
    XAXIS_MIN = 0.1
    XAXIS_MAX = 1.1
    ax1.set_xlabel("Fraction of Attributes Projected", fontproperties=LABEL_FP)
    ax1.set_xlim([XAXIS_MIN, XAXIS_MAX])

    for label in ax1.get_yticklabels() :
        label.set_fontproperties(TICK_FP)
    for label in ax1.get_xticklabels() :
        label.set_fontproperties(TICK_FP)

    return (fig)

def create_selectivity_line_chart(datasets):
    fig = plot.figure()
    ax1 = fig.add_subplot(111)

    # X-AXIS
    x_values = SELECTIVITY
    N = len(x_values)
    x_labels = x_values

    num_items = len(LAYOUTS);
    ind = np.arange(N)
    idx = 0

    # GROUP
    for group_index, group in enumerate(LAYOUTS):
        group_data = []

        # LINE
        for line_index, line in enumerate(x_values):
            group_data.append(datasets[group_index][line_index][1])

        LOG.info("%s group_data = %s ", group, str(group_data))

        ax1.plot(x_values, group_data, color=OPT_LINE_COLORS[idx], linewidth=OPT_LINE_WIDTH,
                 marker=OPT_MARKERS[idx], markersize=OPT_MARKER_SIZE, label=str(group))

        idx = idx + 1

    # GRID
    axes = ax1.get_axes()
    makeGrid(ax1)

    # Y-AXIS
    ax1.yaxis.set_major_locator(LinearLocator(YAXIS_TICKS))
    ax1.minorticks_off()
    ax1.set_ylabel("Execution time (ms)", fontproperties=LABEL_FP)
    #ax1.set_yscale('log', basey=2)

    # X-AXIS
    XAXIS_MIN = 0.1
    XAXIS_MAX = 1.1
    ax1.set_xlabel("Fraction of Tuples Selected", fontproperties=LABEL_FP)
    ax1.set_xlim([XAXIS_MIN, XAXIS_MAX])

    for label in ax1.get_yticklabels() :
        label.set_fontproperties(TICK_FP)
    for label in ax1.get_xticklabels() :
        label.set_fontproperties(TICK_FP)

    return (fig)

def create_operator_line_chart(datasets):
    fig = plot.figure()
    ax1 = fig.add_subplot(111)

    # X-AXIS
    x_values = PROJECTIVITY
    N = len(x_values)
    x_labels = x_values

    num_items = len(LAYOUTS);
    ind = np.arange(N)
    idx = 0

    YLIMIT = 0

    # GROUP
    for group_index, group in enumerate(LAYOUTS):
        group_data = []

        # LINE
        for line_index, line in enumerate(x_values):
            group_data.append(datasets[group_index][line_index][1])

        LOG.info("%s group_data = %s ", group, str(group_data))

        ax1.plot(x_values, group_data, color=OPT_LINE_COLORS[idx], linewidth=OPT_LINE_WIDTH,
                 marker=OPT_MARKERS[idx], markersize=OPT_MARKER_SIZE, label=str(group))

        idx = idx + 1

        YLIMIT = max(YLIMIT, max(group_data))

    # GRID
    axes = ax1.get_axes()
    makeGrid(ax1)

    YLIMIT = next_power_of_10(YLIMIT)

    # Y-AXIS
    ax1.yaxis.set_major_locator(LinearLocator(YAXIS_TICKS))
    ax1.minorticks_off()
    ax1.set_ylabel("Execution time (ms)", fontproperties=LABEL_FP)
    #ax1.set_yscale('log', basey=2)

    # X-AXIS
    XAXIS_MIN = 0.1
    XAXIS_MAX = 1.1
    ax1.set_xlabel("Fraction of Tuples Selected", fontproperties=LABEL_FP)
    ax1.set_xlim([XAXIS_MIN, XAXIS_MAX])

    for label in ax1.get_yticklabels() :
        label.set_fontproperties(TICK_FP)
    for label in ax1.get_xticklabels() :
        label.set_fontproperties(TICK_FP)

    return (fig)

def create_ycsb_bar_chart(datasets):
    fig = plot.figure()
    ax1 = fig.add_subplot(111)

    x_values = YCSB_OPERATIONS
    N = len(x_values)
    x_labels = YCSB_OPERATIONS

    ind = np.arange(N)
    margin = 0.15
    width = ((1.0 - 2 * margin) / N) * 2
    bars = [None] * len(LAYOUTS) * N

    for group in xrange(len(datasets)):
        # GROUP
        latencies = []

        for line in  xrange(len(datasets[group])):
            for col in  xrange(len(datasets[group][line])):
                if col == 1:
                    latencies.append(datasets[group][line][col])

        LOG.info("%s latencies = %s ", LAYOUTS[group], str(latencies))

        bars[group] = ax1.bar(ind + margin + (group * width), latencies, width,
                              color=OPT_COLORS[group],
                              hatch=OPT_PATTERNS[group*2],
                              linewidth=BAR_LINEWIDTH)


    # GRID
    axes = ax1.get_axes()
    #axes.set_ylim(0.01, 1000000)
    makeGrid(ax1)

    # Y-AXIS
    ax1.set_ylabel("Execution time (ms)", fontproperties=LABEL_FP)
    ax1.yaxis.set_major_locator(LinearLocator(YAXIS_TICKS))
    ax1.minorticks_off()

    # X-AXIS
    #ax1.set_xlabel("Number of transactions", fontproperties=LABEL_FP)
    ax1.set_xticklabels(x_labels)
    ax1.set_xticks(ind + 0.5)
    ax1.tick_params(axis='x', which='both', bottom='off', top='off')

    for label in ax1.get_yticklabels() :
        label.set_fontproperties(TICK_FP)
    for label in ax1.get_xticklabels() :
        label.set_fontproperties(TICK_FP)

    return (fig)

###################################################################################
# PLOT HELPERS
###################################################################################

# PROJECTIVITY -- PLOT
def projectivity_plot():

    column_count_type = 0
    for column_count in COLUMN_COUNTS:
        column_count_type = column_count_type + 1

        for write_ratio in WRITE_RATIOS:

            for operator in OPERATORS:
                print(operator)
                datasets = []

                for layout in LAYOUTS:
                    data_file = PROJECTIVITY_DIR + "/" + layout + "/" + operator + "/" + str(column_count) + "/" + str(write_ratio) + "/" + "projectivity.csv"

                    dataset = loadDataFile(10, 2, data_file)
                    datasets.append(dataset)

                fig = create_projectivity_line_chart(datasets)

                if write_ratio == 0:
                    write_mix = "rd"
                else:
                    write_mix = "rw"

                if column_count_type == 1:
                    table_type = "narrow"
                else:
                    table_type = "wide"

                fileName = "projectivity-" + operator + "-" + table_type + "-" + write_mix + ".pdf"

                saveGraph(fig, fileName, width= OPT_GRAPH_WIDTH, height=OPT_GRAPH_HEIGHT/2.0)

# SELECTIVITY -- PLOT
def selectivity_plot():

    column_count_type = 0
    for column_count in COLUMN_COUNTS:
        column_count_type = column_count_type + 1

        for write_ratio in WRITE_RATIOS:

            for operator in OPERATORS:
                print(operator)
                datasets = []

                for layout in LAYOUTS:
                    data_file = SELECTIVITY_DIR + "/" + layout + "/" + operator  + "/" + str(column_count) + "/" + str(write_ratio) + "/" + "selectivity.csv"

                    dataset = loadDataFile(10, 2, data_file)
                    datasets.append(dataset)

                fig = create_selectivity_line_chart(datasets)

                if write_ratio == 0:
                    write_mix = "rd"
                else:
                    write_mix = "rw"

                if column_count_type == 1:
                    table_type = "narrow"
                else:
                    table_type = "wide"

                fileName = "selectivity-" + operator + "-" + table_type + "-" + write_mix + ".pdf"

                saveGraph(fig, fileName, width= OPT_GRAPH_WIDTH, height=OPT_GRAPH_HEIGHT/2.0)

# OPERATOR -- PLOT
def operator_plot():

    column_count_type = 0
    for column_count in COLUMN_COUNTS:
        column_count_type = column_count_type + 1

        for write_ratio in WRITE_RATIOS:

            projectivity_type = 0
            for projectivity in OP_PROJECTIVITY:
                projectivity_type = projectivity_type + 1
                print(projectivity)
                datasets = []

                for layout in LAYOUTS:
                    if projectivity == 1.0: projectivity = 1
                    data_file = OPERATOR_DIR + "/" + layout + "/" + str(projectivity) + "/" + str(column_count) + "/" + str(write_ratio) + "/" + "operator.csv"

                    dataset = loadDataFile(10, 2, data_file)
                    datasets.append(dataset)

                fig = create_operator_line_chart(datasets)

                if write_ratio == 0:
                    write_mix = "rd"
                else:
                    write_mix = "rw"

                if column_count_type == 1:
                    table_type = "narrow"
                else:
                    table_type = "wide"

                fileName = "operator-" + str(projectivity_type) + "-" + table_type + "-" + write_mix + ".pdf"

                saveGraph(fig, fileName, width= OPT_GRAPH_WIDTH, height=OPT_GRAPH_HEIGHT/2.0)


# YCSB -- PLOT
def ycsb_plot():

    column_count = 200
    datasets = []

    for layout in LAYOUTS:
        data_file = YCSB_DIR + "/" + layout + "/" + str(column_count) + "/" + "ycsb.csv"

        dataset = loadDataFile(6, 2, data_file)
        datasets.append(dataset)

    fig = create_ycsb_bar_chart(datasets)

    fileName = "ycsb.pdf"

    saveGraph(fig, fileName, width=OPT_GRAPH_WIDTH, height=OPT_GRAPH_HEIGHT/2.0)


###################################################################################
# EVAL HELPERS
###################################################################################

# CLEAN UP RESULT DIR
def clean_up_dir(result_directory):

    subprocess.call(['rm', '-rf', result_directory])
    if not os.path.exists(result_directory):
        os.makedirs(result_directory)

# RUN EXPERIMENT
def run_experiment(program,
                   scale_factor,
                   transaction_count,
                   experiment_type):

    # cleanup
    subprocess.call(["rm -f " + OUTPUT_FILE], shell=True)

    subprocess.call([program,
                     "-e", str(experiment_type),
                     "-k", str(scale_factor),
                     "-t", str(transaction_count)])


# COLLECT STATS
def collect_stats(result_dir,
                  result_file_name,
                  category):

    fp = open(OUTPUT_FILE)
    lines = fp.readlines()
    fp.close()

    for line in lines:
        data = line.split()

        # Collect info
        layout = data[0]
        operator = data[1]
        selectivity = data[2]
        projectivity = data[3]
        column_count = data[4]
        write_ratio = data[5]
        stat = data[6]

        if(layout == "0"):
            layout = "row"
        elif(layout == "1"):
            layout = "column"
        elif(layout == "2"):
            layout = "hybrid"

        if(operator == "1"):
            operator = "direct"
        elif(operator == "2"):
            operator = "aggregate"

        # PROJECTIVITY/SELECTIVITY CATEGORY
        if category == 1 or category == 2:
            result_directory = result_dir + "/" + layout + "/" + operator + "/" + column_count + "/" + write_ratio
        # OPERATOR CATEGORY
        elif category == 3:
            result_directory = result_dir + "/" + layout + "/" + str(projectivity) + "/" + column_count + "/" + write_ratio

        if not os.path.exists(result_directory):
            os.makedirs(result_directory)
        file_name = result_directory + "/" + result_file_name

        result_file = open(file_name, "a")

        # PROJECTIVITY/SELECTIVITY CATEGORY
        if category == 1:
            result_file.write(str(projectivity) + " , " + str(stat) + "\n")
        # OPERATOR CATEGORY
        elif category == 2 or category == 3:
            result_file.write(str(selectivity) + " , " + str(stat) + "\n")

        result_file.close()

# COLLECT STATS
def collect_ycsb_stats(result_dir,
                       result_file_name):

    fp = open(OUTPUT_FILE)
    lines = fp.readlines()
    fp.close()

    for line in lines:
        data = line.split()

        # Collect info
        layout = data[0]
        operator = data[1]
        column_count = data[2]
        stat = data[3]

        if(layout == "0"):
            layout = "row"
        elif(layout == "1"):
            layout = "column"
        elif(layout == "2"):
            layout = "hybrid"

        result_directory = result_dir + "/" + layout + "/" + column_count

        if not os.path.exists(result_directory):
            os.makedirs(result_directory)
        file_name = result_directory + "/" + result_file_name

        result_file = open(file_name, "a")
        result_file.write(str(operator) + " , " + str(stat) + "\n")
        result_file.close()

###################################################################################
# EVAL
###################################################################################

# PROJECTIVITY -- EVAL
def projectivity_eval():

    # CLEAN UP RESULT DIR
    clean_up_dir(PROJECTIVITY_DIR)

    # RUN EXPERIMENT
    run_experiment(HYADAPT, SCALE_FACTOR,
                   TRANSACTION_COUNT, PROJECTIVITY_EXPERIMENT)

    # COLLECT STATS
    collect_stats(PROJECTIVITY_DIR, "projectivity.csv", 1)

# SELECTIVITY -- EVAL
def selectivity_eval():

    # CLEAN UP RESULT DIR
    clean_up_dir(SELECTIVITY_DIR)

    # RUN EXPERIMENT
    run_experiment(HYADAPT, SCALE_FACTOR,
                   TRANSACTION_COUNT, SELECTIVITY_EXPERIMENT)

    # COLLECT STATS
    collect_stats(SELECTIVITY_DIR, "selectivity.csv", 2)

# OPERATOR -- EVAL
def operator_eval():

    # CLEAN UP RESULT DIR
    clean_up_dir(OPERATOR_DIR)

    # RUN EXPERIMENT
    run_experiment(HYADAPT, SCALE_FACTOR,
                   TRANSACTION_COUNT, OPERATOR_EXPERIMENT)

    # COLLECT STATS
    collect_stats(OPERATOR_DIR, "operator.csv", 3)

# YCSB -- EVAL
def ycsb_eval():

    # CLEAN UP RESULT DIR
    clean_up_dir(YCSB_DIR)

    # RUN EXPERIMENT
    run_experiment(YCSB, YCSB_SCALE_FACTOR,
                   YCSB_TRANSACTION_COUNT, YCSB_EXPERIMENT)

    # COLLECT STATS
    collect_ycsb_stats(YCSB_DIR, "ycsb.csv")

###################################################################################
# MAIN
###################################################################################
if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Run Tilegroup Experiments')

    parser.add_argument("-p", "--projectivity", help='eval projectivity', action='store_true')
    parser.add_argument("-s", "--selectivity", help='eval selectivity', action='store_true')
    parser.add_argument("-o", "--operator", help='eval operator', action='store_true')
    parser.add_argument("-y", "--ycsb", help='eval ycsb', action='store_true')

    parser.add_argument("-a", "--projectivity_plot", help='plot projectivity', action='store_true')
    parser.add_argument("-b", "--selectivity_plot", help='plot selectivity', action='store_true')
    parser.add_argument("-c", "--operator_plot", help='plot operator', action='store_true')
    parser.add_argument("-d", "--ycsb_plot", help='plot operator', action='store_true')

    args = parser.parse_args()

    if args.projectivity:
        projectivity_eval()

    if args.projectivity_plot:
        projectivity_plot();

    if args.selectivity:
        selectivity_eval()

    if args.selectivity_plot:
        selectivity_plot();

    if args.operator:
        operator_eval()

    if args.operator_plot:
        operator_plot();

    if args.ycsb:
        ycsb_eval()

    if args.ycsb_plot:
        ycsb_plot()

    #create_legend()
    #create_bar_legend()



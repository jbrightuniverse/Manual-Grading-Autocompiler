"""

A script to convert PrairieLearn's manual grading files to grader-friendly targeted CSVs.
See README.md for instructions on how to set up the folderstructure.

Originally written by James Yuming Yu, 2021
github: jbrightuniverse
Released under the MIT License.

"""

import csv
from collections import defaultdict

from shutil import copyfile
import os
import sys
import json
import argparse

COURSE_NAME = "CPSC_213_2021W2" # the name of the course on PrairieLearn
MAX_ASSIGNMENT = 11 # maximum assignment number, just as a bounds check

# Commandline UI setup
parser = argparse.ArgumentParser(description="Convert PrairieLearn's manual grading files to grader-friendly targeted CSVs. \n" + 
"Before running, ensure that:\n" +
" - A file called AX_rubric.json exists in the parent directory \n" +
" - A PL .csv grading file exists in the parent directory \n" +
" - You have unzipped the contents of the manual grading zip file from PL in the parent directory", formatter_class=argparse.RawTextHelpFormatter)
parser.add_argument('assignment_num', type=int, help='The assignment number')
parser.add_argument('-g', '--gradeall', action='store_true', default=False, help='Set flag if you wish to grade ALL questions. Do not set flag if you wish to only mark non-autograded questions')
parser.add_argument('-d', '--directory', type=str, metavar='PATH', help="Set path to parent directory of assignment files. Defaults to AX where X is the assignment number.")
parser.add_argument('-c', '--coursename', type=str, metavar='COURSE', default=str(COURSE_NAME), help=f'Set the course name prefix. Default value "{COURSE_NAME}" can be edited in the script source code')

namespace = parser.parse_args()
assignment = namespace.assignment_num
gradeAllSubmissions = namespace.gradeall
if(namespace.directory):
    pathToParentDir = namespace.directory
else:
    pathToParentDir = "A" + str(assignment)
courseName = namespace.coursename

# Existence check for parent directory
if not os.path.exists(pathToParentDir):
    print(f'Invalid path to parent directory: "{pathToParentDir}"')
    sys.exit()

# SAFETY GUARD: if the grading files already exist, suspend the program to prevent in-progress CSV files from being overwritten
# DO NOT REMOVE
# to unlock safety guard, delete the 'AX_to_grade' folder created by the program
try:
    # if the files don't exist, create a folder of the form 'AX/AX_to_grade' where X is the assignment number
    os.mkdir(f"{pathToParentDir}/A{assignment}_to_grade")
except:
    print("GRADING IN PROGRESS, FILE SUSPENDED.")
    sys.exit()

# Existence check for rubric file
if not os.path.exists(f"{pathToParentDir}/A{assignment}_rubric.json"):
    print(f'No Rubric json was found under:"{pathToParentDir}"')
    sys.exit()

# Load rubric data
with open(f"{pathToParentDir}/A{assignment}_rubric.json") as f:
    rubric_json = json.load(f)

assignmentcollector = defaultdict(list)


the_grading_filename = [f"{pathToParentDir}/{courseName}_A{assignment}_submissions_for_manual_grading.csv", f"A{assignment}/{COURSE_NAME}_A{assignment}_final_submissions.csv"][gradeAllSubmissions == True]

# Existence check for grading csv file
if not os.path.exists(the_grading_filename):
    print(f'No grading csv file found under:"{pathToParentDir}"')
    sys.exit()

# Existence check for unzipped submissions folder
if not os.path.exists(f"{pathToParentDir}/Assignment{assignment}"):
    print(f'No Unzipped submission folder found under:"{pathToParentDir}". Ensure file name has format AssignmentX, where X is the assignment number')
    sys.exit()

with open(the_grading_filename) as f:
    lines = csv.reader(f, delimiter = ',', quotechar = '"')
    rows = [l for l in lines]
    keys = rows[0]
    # switch between group assignments and individual assignments based on the CSV keys provided
    if "group_name" in keys:
        keyoperator = ["group_name", "qid", "instance", "points", "feedback"]
    else:
        keyoperator = ["uid", "qid", "instance", "points", "feedback"]

    # for all submissions in the csv:
    for row in rows[1:]:
        if gradeAllSubmissions == True or row[keys.index("old_feedback")] == '':
            # sort the questions of each student into a folder-specific file
            # only require important data: uid, qid, points, feedback
            # the dummy field with key "instance" and value 1 needs to exist in every row
            QID_NAME = ["qid", "Question"][gradeAllSubmissions == True]
            GROUP_NAME = ["group_name", "Group name"][gradeAllSubmissions == True]
            UID_NAME = ["uid", "UID"][gradeAllSubmissions == True]
            
            # generate some precompiled feedback
            feedback = "Rubric:</br></br>" + "</br>".join(rubric_json[row[keys.index(QID_NAME)]]["general_comment"]) + "</br></br>"
            if GROUP_NAME in keys:
                newrow = [row[keys.index(GROUP_NAME)], row[keys.index(QID_NAME)], 1, '', feedback]
            else:
                newrow = [row[keys.index(UID_NAME)], row[keys.index(QID_NAME)], 1, '', feedback]
            
            assignmentcollector[row[keys.index(QID_NAME)]].append(newrow)

    # iterate over questions
    for key in assignmentcollector:
        print("RUNNING " + key)

        # THIS BUILDS THE ACTUAL QUESTION-SPECIFIC FILE
        try:
            os.mkdir(f"{pathToParentDir}/A{assignment}_to_grade/{key.split('/')[0]}")
        except: pass # make an assignment-specific folder - some assignments take questions from more than one "assignment bank"

        try:
            os.mkdir(f"{pathToParentDir}/A{assignment}_to_grade/{key}")
        except: pass # question-specific subfolder

        # THIS CONSTRUCTS THE CSV
        with open(f"{pathToParentDir}/A{assignment}_to_grade/{key}/{key.replace('/', '_')}_TO_GRADE.csv", "w", newline = '') as f2:
            writer = csv.writer(f2, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL) 

            # put the CSV key into the file
            writer.writerow(keyoperator)
            # put the students into the file
            for row in sorted(assignmentcollector[key], key = lambda x: x[0].lower()):
                writer.writerow(row)
        
        # THIS PUTS THE FILES ASSOCIATED WITH THE CSV IN THE CORRESPONDING FOLDER
        for row in assignmentcollector[key]:
            print("    copying " + row[0])
            try:
                # create a group/student-specific folder within the question subfolder
                os.mkdir(f"{pathToParentDir}/A{assignment}_to_grade/{key}/{row[0]}")
            except: pass # again, skip if exists

            for foldername in os.listdir(f"{pathToParentDir}/Assignment{assignment}"):
                amount_to_remove = [1, 2][gradeAllSubmissions == True]
                if "_".join(foldername.split("_")[:-amount_to_remove]) == row[0]:
                    target_assignment = foldername.split("_")[-1]
                    for filename in os.listdir(f"A{assignment}/Assignment{assignment}/{foldername}"):
                        if (target_assignment+"/"+filename).startswith(key):
                            copyfile(f"{pathToParentDir}/Assignment{assignment}/{foldername}/{filename}", f"A{assignment}/A{assignment}_to_grade/{key}/{row[0]}/{filename}")

# CREATE TXT FILES WITH SUBMISSION TEXT IN THEM FOR EASY VIEWING
for sub_assignment in os.listdir(f"{pathToParentDir}/A{assignment}_to_grade"):
    print(sub_assignment, "producing TXT file...")
    for question in os.listdir(f"{pathToParentDir}/A{assignment}_to_grade/{sub_assignment}"):
        print(f"    {question}")
        with open(f"{pathToParentDir}/A{assignment}_to_grade/{sub_assignment}/{question}/{sub_assignment+'_'+question}_aggregate_submissions.txt", "w", encoding='latin-1') as f:
            collected_cwls = []
            for cwl in os.listdir(f"{pathToParentDir}/A{assignment}_to_grade/{sub_assignment}/{question}"):
                # check that this is actually a CWL folder
                if os.path.isdir(f"{pathToParentDir}/A{assignment}_to_grade/{sub_assignment}/{question}/{cwl}"):
                    collected_cwls.append(cwl)
            collected_cwls.sort(key = lambda x: x.lower()) # alphabetical sort
            for cwl in collected_cwls:
                f.write("* BEGIN NEW CWL or NAME ***************************************************\n")
                f.write("***************************************************************************\n")
                f.write("***\n")
                f.write("*** CWL or NAME: " + cwl + "\n")
                for codefile in os.listdir(f"{pathToParentDir}/A{assignment}_to_grade/{sub_assignment}/{question}/{cwl}"):
                    f.write("***\n")
                    f.write("----- BEGIN NEW FILE ------------------------------------------------------\n")
                    filename = "_".join(codefile.replace(question + "_", "").split("_")[1:])
                    f.write("***\n")
                    f.write("*** FILENAME: " + filename+" (CWL or NAME: "+ cwl+")\n")
                    f.write("***\n")
                    f.write("***\n")
                    f.write("***\n")
                    with open(f"{pathToParentDir}/A{assignment}_to_grade/{sub_assignment}/{question}/{cwl}/{codefile}",encoding='latin-1') as f2:
                        for line in f2:
                            f.write(line)
                    f.write("***\n")
                    f.write("***\n")
                    f.write("***\n")

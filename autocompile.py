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

COURSE_NAME = "CPSC_213_2021W2" # the name of the course on PrairieLearn
MAX_ASSIGNMENT = 11 # maximum assignment number, just as a bounds check
GRADE_ALL_SUBMISSIONS = False # change this to True if you wish to grade all submissions rather than only the ones that have not been autograded
# relevant for assignments where the autograder only checks for completion and not correctness


# verify that an assignment number was given on the command line
# should just be a number, no "A"
try:
    assignment = sys.argv[1]
except:
    print("USAGE: python3 autocompile.py <assignment_number>")
    sys.exit()

# assignment should be an integer
try:
    assignment = int(assignment)
except:
    print("Assignment must be an integer!")
    sys.exit()

# assignment should be valid
if assignment not in range(1, MAX_ASSIGNMENT+1):
    print("Invalid assignment ID.")
    sys.exit()

# SAFETY GUARD: if the grading files already exist, suspend the program to prevent in-progress CSV files from being overwritten
# DO NOT REMOVE
# to unlock safety guard, delete the 'AX_to_grade' folder created by the program
try:
    # if the files don't exist, create a folder of the form 'AX/AX_to_grade' where X is the assignment number
    os.mkdir(f"A{assignment}/A{assignment}_to_grade")
except: 
    print("GRADING IN PROGRESS, FILE SUSPENDED.")
    sys.exit()

assignmentcollector = defaultdict(list)

with open(f"A{assignment}/A{assignment}_rubric.json") as f:
    rubric_json = json.load(f)

the_grading_filename = [f"A{assignment}/{COURSE_NAME}_A{assignment}_submissions_for_manual_grading.csv", f"A{assignment}/{COURSE_NAME}_A{assignment}_final_submissions.csv"][GRADE_ALL_SUBMISSIONS == True]
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
        if GRADE_ALL_SUBMISSIONS == True or row[keys.index("old_feedback")] == '':
            # sort the questions of each student into a folder-specific file
            # only require important data: uid, qid, points, feedback
            # the dummy field with key "instance" and value 1 needs to exist in every row
            QID_NAME = ["qid", "Question"][GRADE_ALL_SUBMISSIONS == True]
            GROUP_NAME = ["group_name", "Group name"][GRADE_ALL_SUBMISSIONS == True]
            UID_NAME = ["uid", "UID"][GRADE_ALL_SUBMISSIONS == True]
            
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
            os.mkdir(f"A{assignment}/A{assignment}_to_grade/{key.split('/')[0]}")
        except: pass # make an assignment-specific folder - some assignments take questions from more than one "assignment bank"

        try:
            os.mkdir(f"A{assignment}/A{assignment}_to_grade/{key}")
        except: pass # question-specific subfolder

        # THIS CONSTRUCTS THE CSV
        with open(f"A{assignment}/A{assignment}_to_grade/{key}/{key.replace('/', '_')}_TO_GRADE.csv", "w", newline = '') as f2:
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
                os.mkdir(f"A{assignment}/A{assignment}_to_grade/{key}/{row[0]}")
            except: pass # again, skip if exists

            for foldername in os.listdir(f"A{assignment}/Assignment{assignment}"):
                amount_to_remove = [1, 2][GRADE_ALL_SUBMISSIONS == True]
                if "_".join(foldername.split("_")[:-amount_to_remove]) == row[0]:
                    target_assignment = foldername.split("_")[-1]
                    for filename in os.listdir(f"A{assignment}/Assignment{assignment}/{foldername}"):
                        if (target_assignment+"/"+filename).startswith(key):
                            copyfile(f"A{assignment}/Assignment{assignment}/{foldername}/{filename}", f"A{assignment}/A{assignment}_to_grade/{key}/{row[0]}/{filename}")

# CREATE TXT FILES WITH SUBMISSION TEXT IN THEM FOR EASY VIEWING
for sub_assignment in os.listdir(f"A{assignment}/A{assignment}_to_grade"):
    print(sub_assignment, "producing TXT file...")
    for question in os.listdir(f"A{assignment}/A{assignment}_to_grade/{sub_assignment}"):
        print(f"    {question}")
        with open(f"A{assignment}/A{assignment}_to_grade/{sub_assignment}/{question}/{sub_assignment+'_'+question}_aggregate_submissions.txt", "w", encoding='latin-1') as f:
            collected_cwls = []
            for cwl in os.listdir(f"A{assignment}/A{assignment}_to_grade/{sub_assignment}/{question}"):
                # check that this is actually a CWL folder
                if os.path.isdir(f"A{assignment}/A{assignment}_to_grade/{sub_assignment}/{question}/{cwl}"):
                    collected_cwls.append(cwl)
            collected_cwls.sort(key = lambda x: x.lower()) # alphabetical sort
            for cwl in collected_cwls:
                f.write("* BEGIN NEW CWL or NAME ***************************************************\n")
                f.write("***************************************************************************\n")
                f.write("***\n")
                f.write("*** CWL or NAME: " + cwl + "\n")
                for codefile in os.listdir(f"A{assignment}/A{assignment}_to_grade/{sub_assignment}/{question}/{cwl}"):
                    f.write("***\n")
                    f.write("----- BEGIN NEW FILE ------------------------------------------------------\n")
                    filename = "_".join(codefile.replace(question + "_", "").split("_")[1:])
                    f.write("***\n")
                    f.write("*** FILENAME: " + filename+" (CWL or NAME: "+ cwl+")\n")
                    f.write("***\n")
                    f.write("***\n")
                    f.write("***\n")
                    with open(f"A{assignment}/A{assignment}_to_grade/{sub_assignment}/{question}/{cwl}/{codefile}",encoding='latin-1') as f2:
                        for line in f2:
                            f.write(line)
                    f.write("***\n")
                    f.write("***\n")
                    f.write("***\n")

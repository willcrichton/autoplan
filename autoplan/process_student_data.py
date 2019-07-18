# process_student_data.py
# -----------------------------
# Module responsible for processing student's raw data. 
# 
# Assumptions: 
# a. Student data is located in autoplan/autoplan/data/raw/[problem-name]/
# b. Within /[problem-name], each student corresponds to a folder
# c. Folders contain variable number of files. Empty submission files are named 'submission_dirs_with_no_files.txt'.
# d. Only the latest submission is analyzed and labeled. 
#   
# Output:
# a. TODO: list outputs specifically here
# Unclear as if the best strategy is to retain students ID or to just return all solutions
 
import os
import glob
import re

def get_directory_list():
	path = "../data/raw/pythagorean/"
	dirlist = [folder for folder in os.listdir(path) if os.path.isdir(os.path.join(path, folder))]
	return dirlist

def get_last_submission(dirlist):
	empty_submission = "submission_dirs_with_no_files.txt"
	for student_folder in dirlist:     # Gets individual student directories
		all_submissions = glob.glob(path + student_folder + '/*')
		last_submission = max(all_submissions, key=os.path.getctime)
	
		solutions = []
		if not last_submission.endswith(empty_submission): 
			with open(last_submission, 'r') as file:
				solution = file.read()
				solutions.append(solution)
	return solutions	

# Source: github.com/malik-ali/generative-grading/
def remove_comments(program_string): 
    def replacer(match):
        s = match.group(0)
        if s.startswith('/'):
            return " " # note: a space and not an empty string
        else:
            return s

    pattern = re.compile(
        r'//.*?$|/\*.*?\*/|\'(?:\\.|[^\\\'])*\'|"(?:\\.|[^\\"])*"',
        re.DOTALL | re.MULTILINE
    )
    return re.sub(pattern, replacer, program_string)



# Code to run on the fly and test:
# path = "../data/raw/pythagorean/"
# empty_submission = "submission_dirs_with_no_files.txt"
# dirlist = [folder for folder in os.listdir(path) if os.path.isdir(os.path.join(path, folder))]

# c = 0
# for student_folder in dirlist:     # Gets individual student directories
# 	all_submissions = glob.glob(path + student_folder + '/*')
# 	last_submission = max(all_submissions, key=os.path.getctime)
	
# 	if not last_submission.endswith(empty_submission): 
# 		with open(last_submission, 'r') as file:
# 			solution = file.read()
# 			clean = remove_comments(solution)
# 			if c < 2:
# 				print(clean)
# 	c += 1

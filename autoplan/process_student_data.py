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
from torch.utils.data import Dataset as TorchDataset, DataLoader
from typing import List, Dict
from .labels import Labels
from .dataset import Dataset 

def get_directory_list():
	path = "../data/raw/pythagorean/"
	dirlist = [folder for folder in os.listdir(path) if os.path.isdir(os.path.join(path, folder))]
	return dirlist

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

# Returns a dict {'student_ID', 'student_last_solution'}
def get_last_submission(dirlist):
	empty_submission = "submission_dirs_with_no_files.txt"
	solutions = {}
	
	for student_folder in dirlist:     # Gets individual student directories
		all_submissions = glob.glob(path + student_folder + '/*')
		last_submission = max(all_submissions, key=os.path.getctime)
	
		if not last_submission.endswith(empty_submission): 
			with open(last_submission, 'r') as file:
				solution = file.read()
				uncommented_solution = remove_comments(solution)
				solutions[student_folder] = uncommented_solution
	return solutions	


@dataclass
class StudentDataset(Dataset):

	def build_student_dataset(synthetic_dataset, programs, tokenizer):

# token_indices - got it after tokenizing
# choice_index_map - choice_indices synthetic
# program_labels - we can generate using torch (but still needs labels, choices)

		data = # TODO 

		# These are the same as the synthetic dataset
		vocab_size = synthetic_dataset.vocab_size
		label_set = synthetic_dataset.label_set
        class_balance = synthetic_dataset.class_balance
        choices = synthetic_dataset.choices,
        choice_indices = synthetic_dataset.choice_indices

		return Dataset(data=data,
                   vocab_size=vocab_size,
                   label_set=label_list,
                   class_balance=class_balance,
                   choices=all_choices,
                   choice_indices=choice_indices) 


# ------------------------------
# Code to run on the fly and test:
# path = "../data/raw/pythagorean/"
# empty_submission = "submission_dirs_with_no_files.txt"
# dirlist = [folder for folder in os.listdir(path) if os.path.isdir(os.path.join(path, folder))]

# c = 0
# solutions = {}
# for student_folder in dirlist:     # Gets individual student directories
# 	all_submissions = glob.glob(path + student_folder + '/*')
# 	last_submission = max(all_submissions, key=os.path.getctime)
	
# 	if not last_submission.endswith(empty_submission): 
# 		with open(last_submission, 'r') as file:
# 			solution = file.read()
# 			uncommented_solution = remove_comments(solution)
# 			solutions[student_folder] = uncommented_solution
# 			if c < 5:
# 				print(solutions)
# 	c += 1

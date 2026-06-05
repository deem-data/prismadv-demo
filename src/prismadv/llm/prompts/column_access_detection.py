from inspect import cleandoc

COLUMN_ACCESS_DETECTION_PROMPT = cleandoc(
    """You are part of the task-aware data validation system. The system is designed to generate data quality constraints tailored to specific downstream tasks by analyzing both the dataset and the code that processes it.

You serve as the *Column Access Detection* component. You are responsible for identifying which columns from the dataset are actually accessed or utilized in the provided code snippet so that we can focus our constraint generation efforts on these relevant columns.

Please only return the column names exactly as they appear in the raw table definition (`{columns_desc}`). For derived columns, map them back and return only the original raw column names used to derive them.

The dataset is a table with the following columns:
{columns_desc}

The user writes the code snippet below:
{code_script}

The above code snippet is used for the following downstream task:
{downstream_task_description}

Your response should be a list of comma-separated values
eg: `foo, bar, baz`
"""
)


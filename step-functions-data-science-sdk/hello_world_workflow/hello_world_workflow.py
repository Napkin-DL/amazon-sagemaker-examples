#!/usr/bin/env python
# coding: utf-8

# # AWS Step Functions Data Science SDK - Hello World
# 1. [Introduction](#Introduction)
# 1. [Setup](#Setup)
# 1. [Create steps for your workflow](#Create-steps-for-your-workflow)
# 1. [Define the workflow instance](#Define-the-workflow-instance)
# 1. [Review the Amazon States Language code for your workflow](#Review-the-Amazon-States-Language-code-for-your-workflow)
# 1. [Create the workflow on AWS Step Functions](#Create-the-workflow-on-AWS-Step-Functions)
# 1. [Execute the workflow](#Execute-the-workflow)
# 1. [Review the execution progress](#Review-the-execution-progress)
# 1. [Review the execution history](#Review-the-execution-history)
# 

# ## Introduction
# 
# This notebook describes using the AWS Step Functions Data Science SDK to create and manage workflows. The Step Functions SDK is an open source library that allows data scientists to easily create and execute machine learning workflows using AWS Step Functions and Amazon SageMaker. For more information, see the following.
# * [AWS Step Functions](https://aws.amazon.com/step-functions/)
# * [AWS Step Functions Developer Guide](https://docs.aws.amazon.com/step-functions/latest/dg/welcome.html)
# * [AWS Step Functions Data Science SDK](https://aws-step-functions-data-science-sdk.readthedocs.io)
# 
# In this notebook we will use the SDK to create steps, link them together to create a workflow, and execute the workflow in AWS Step Functions. 

# In[1]:


import sys
get_ipython().system('{sys.executable} -m pip install --upgrade stepfunctions')


# ## Setup
# 
# ### Add a policy to your SageMaker role in IAM
# 
# **If you are running this notebook on an Amazon SageMaker notebook instance**, the IAM role assumed by your notebook instance needs permission to create and run workflows in AWS Step Functions. To provide this permission to the role, do the following.
# 
# 1. Open the Amazon [SageMaker console](https://console.aws.amazon.com/sagemaker/). 
# 2. Select **Notebook instances** and choose the name of your notebook instance
# 3. Under **Permissions and encryption** select the role ARN to view the role on the IAM console
# 4. Choose **Attach policies** and search for `AWSStepFunctionsFullAccess`.
# 5. Select the check box next to `AWSStepFunctionsFullAccess` and choose **Attach policy**
# 
# If you are running this notebook in a local environment, the SDK will use your configured AWS CLI configuration. For more information, see [Configuring the AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html).
# 
# Next, create an execution role in IAM for Step Functions. 
# 
# ### Create an execution role for Step Functions
# 
# You need an execution role so that you can create and execute workflows in Step Functions.
# 
# 1. Go to the [IAM console](https://console.aws.amazon.com/iam/)
# 2. Select **Roles** and then **Create role**.
# 3. Under **Choose the service that will use this role** select **Step Functions**
# 4. Choose **Next** until you can enter a **Role name**
# 5. Enter a name such as `StepFunctionsWorkflowExecutionRole` and then select **Create role**
# 
# 
# Attach a policy to the role you created. The following steps attach a policy that provides full access to Step Functions, however as a good practice you should only provide access to the resources you need.  
# 
# 1. Under the **Permissions** tab, click **Add inline policy**
# 2. Enter the following in the **JSON** tab
# 
# ```json
# {
#     "Version": "2012-10-17",
#     "Statement": [
#         {
#             "Effect": "Allow",
#             "Action": [
#                 "sagemaker:CreateTransformJob",
#                 "sagemaker:DescribeTransformJob",
#                 "sagemaker:StopTransformJob",
#                 "sagemaker:CreateTrainingJob",
#                 "sagemaker:DescribeTrainingJob",
#                 "sagemaker:StopTrainingJob",
#                 "sagemaker:CreateHyperParameterTuningJob",
#                 "sagemaker:DescribeHyperParameterTuningJob",
#                 "sagemaker:StopHyperParameterTuningJob",
#                 "sagemaker:CreateModel",
#                 "sagemaker:CreateEndpointConfig",
#                 "sagemaker:CreateEndpoint",
#                 "sagemaker:DeleteEndpointConfig",
#                 "sagemaker:DeleteEndpoint",
#                 "sagemaker:UpdateEndpoint",
#                 "sagemaker:ListTags",
#                 "lambda:InvokeFunction",
#                 "sqs:SendMessage",
#                 "sns:Publish",
#                 "ecs:RunTask",
#                 "ecs:StopTask",
#                 "ecs:DescribeTasks",
#                 "dynamodb:GetItem",
#                 "dynamodb:PutItem",
#                 "dynamodb:UpdateItem",
#                 "dynamodb:DeleteItem",
#                 "batch:SubmitJob",
#                 "batch:DescribeJobs",
#                 "batch:TerminateJob",
#                 "glue:StartJobRun",
#                 "glue:GetJobRun",
#                 "glue:GetJobRuns",
#                 "glue:BatchStopJobRun"
#             ],
#             "Resource": "*"
#         },
#         {
#             "Effect": "Allow",
#             "Action": [
#                 "iam:PassRole"
#             ],
#             "Resource": "*",
#             "Condition": {
#                 "StringEquals": {
#                     "iam:PassedToService": "sagemaker.amazonaws.com"
#                 }
#             }
#         },
#         {
#             "Effect": "Allow",
#             "Action": [
#                 "events:PutTargets",
#                 "events:PutRule",
#                 "events:DescribeRule"
#             ],
#             "Resource": [
#                 "arn:aws:events:*:*:rule/StepFunctionsGetEventsForSageMakerTrainingJobsRule",
#                 "arn:aws:events:*:*:rule/StepFunctionsGetEventsForSageMakerTransformJobsRule",
#                 "arn:aws:events:*:*:rule/StepFunctionsGetEventsForSageMakerTuningJobsRule",
#                 "arn:aws:events:*:*:rule/StepFunctionsGetEventsForECSTaskRule",
#                 "arn:aws:events:*:*:rule/StepFunctionsGetEventsForBatchJobsRule"
#             ]
#         }
#     ]
# }
# ```
# 
# 3. Choose **Review policy** and give the policy a name such as `StepFunctionsWorkflowExecutionPolicy`
# 4. Choose **Create policy**. You will be redirected to the details page for the role.
# 5. Copy the **Role ARN** at the top of the **Summary**
# 
# ### Import the required modules from the SDK

# In[2]:


import stepfunctions
import logging

from stepfunctions.steps import *
from stepfunctions.workflow import Workflow

stepfunctions.set_stream_logger(level=logging.INFO)

workflow_execution_role = "<execution-role-arn>" # paste the StepFunctionsWorkflowExecutionRole ARN from above


# ## Create steps for your workflow
# 
# In the following cell, you define steps that you will use in our workflow. Steps relate to states in AWS Step Functions. For more information, see [States](https://docs.aws.amazon.com/step-functions/latest/dg/concepts-states.html) in the *AWS Step Functions Developer Guide*. For more information on the AWS Step Functions Data Science SDK APIs, see: https://aws-step-functions-data-science-sdk.readthedocs.io. 
# 

# ### Pass state
# 
# A `Pass` state in Step Functions simply passes its input to its output, without performing work. See [Pass](https://aws-step-functions-data-science-sdk.readthedocs.io/en/latest/states.html#stepfunctions.steps.states.Pass) in the AWS Step Functions Data Science SDK documentation.
# 

# In[3]:


start_pass_state = Pass(
    state_id="MyPassState"             
)


# ### Choice state
# 
# A `Choice` state in Step Functions adds branching logic to your workflow. See [Choice](https://aws-step-functions-data-science-sdk.readthedocs.io/en/latest/states.html#stepfunctions.steps.states.Choice) in the AWS Step Functions Data Science SDK documentation.

# In[4]:


choice_state = Choice(
    state_id="Is this Hello World example?"
)


# First create the steps for the "happy path".

# ### Wait state
# 
# A `Wait` state in Step Functions waits a specific amount of time. See [Wait](https://aws-step-functions-data-science-sdk.readthedocs.io/en/latest/states.html#stepfunctions.steps.states.Wait) in the AWS Step Functions Data Science SDK documentation.

# In[5]:


wait_state = Wait(
    state_id="Wait for 3 seconds",
    seconds=3
)


# ### Parallel state
# 
# A `Parallel` state in Step Functions is used to create parallel branches of execution in your workflow. This creates the `Parallel` step and adds two branches: `Hello` and `World`. See [Parallel](https://aws-step-functions-data-science-sdk.readthedocs.io/en/latest/states.html#stepfunctions.steps.states.Parallel) in the AWS Step Functions Data Science SDK documentation.

# In[6]:


parallel_state = Parallel("MyParallelState")
parallel_state.add_branch(
    Pass(state_id="Hello")
)
parallel_state.add_branch(
    Pass(state_id="World")
)


# ### Lambda Task state
# 
# A `Task` State in Step Functions represents a single unit of work performed by a workflow. Tasks can call Lambda functions and orchestrate other AWS services. See [AWS Service Integrations](https://docs.aws.amazon.com/step-functions/latest/dg/concepts-service-integrations.html) in the *AWS Step Functions Developer Guide*.
# 
# #### Create a Lambda function
# 
# The Lambda task state in this workflow uses a simple Lambda function **(Python 3.x)** that returns a base64 encoded string. Create the following function in the [Lambda console](https://console.aws.amazon.com/lambda/).
# 
# ```python
# import json
# import base64
#  
# def lambda_handler(event, context):
#     return {
#         'statusCode': 200,
#         'input': event['input'],
#         'output': base64.b64encode(event['input'].encode()).decode('UTF-8')
#     }
# ```

# #### Define the Lambda Task state
# 
# The following creates a [LambdaStep](https://aws-step-functions-data-science-sdk.readthedocs.io/en/latest/compute.html#stepfunctions.steps.compute.LambdaStep) called `lambda_state`, and then configures the options to [Retry](https://docs.aws.amazon.com/step-functions/latest/dg/concepts-error-handling.html#error-handling-retrying-after-an-error) if the Lambda function fails.

# In[7]:


lambda_state = LambdaStep(
    state_id="Convert HelloWorld to Base64",
    parameters={  
        "FunctionName": "MyLambda", #replace with the name of the function you created
        "Payload": {  
           "input": "HelloWorld"
        }
    }
)

lambda_state.add_retry(Retry(
    error_equals=["States.TaskFailed"],
    interval_seconds=15,
    max_attempts=2,
    backoff_rate=4.0
))

lambda_state.add_catch(Catch(
    error_equals=["States.TaskFailed"],
    next_step=Fail("LambdaTaskFailed")
))


# ### Succeed state
# 
# A `Succeed` state in Step Functions stops an execution successfully. See [Succeed](https://aws-step-functions-data-science-sdk.readthedocs.io/en/latest/states.html#stepfunctions.steps.states.Succeed) in the AWS Step Functions Data Science SDK documentation.

# In[8]:


succeed_state = Succeed("HelloWorldSuccessful")


# ### Chain together steps for the happy path
# 
# The following links together the steps you've created above in into a sequential group called `happy_path`. The new step sequentially includes the Wait state, the Parallel state, the Lambda state, and the Succeed state that you created earlier. See [Chain](https://aws-step-functions-data-science-sdk.readthedocs.io/en/latest/states.html#stepfunctions.steps.states.Chain) in the AWS Step Functions Data Science SDK documentation.

# In[9]:


happy_path = Chain([wait_state, parallel_state, lambda_state, succeed_state])


# For the sad path, we simply end the workflow using a `Fail` state. See [Fail](https://aws-step-functions-data-science-sdk.readthedocs.io/en/latest/states.html#stepfunctions.steps.states.Fail) in the AWS Step Functions Data Science SDK documentation.

# In[10]:


sad_state = Fail("HelloWorldFailed")


# ### Choice state
# 
# Now, attach branches to the Choice state you created earlier. See *Choice Rules* in the [AWS Step Functions Data Science SDK documentation](https://aws-step-functions-data-science-sdk.readthedocs.io) .

# In[11]:


choice_state.add_choice(
    rule=ChoiceRule.BooleanEquals(variable=start_pass_state.output()["IsHelloWorldExample"], value=True),
    next_step=happy_path
)
choice_state.add_choice(
    ChoiceRule.BooleanEquals(variable=start_pass_state.output()["IsHelloWorldExample"], value=False),
    next_step=sad_state
)


# ## Define the workflow instance
# 
# The following cell defines the workflow. First, it chains tother the Pass state and the Choice states defined above. The other states have been chained into `happy_path` and `sad_path` steps that are selected by the Choice state.

# In[12]:


# First we chain the start pass state and the choice state
workflow_definition=Chain([start_pass_state, choice_state])

# Next, we define the workflow
workflow = Workflow(
    name="MyWorkflow_v12341",
    definition=workflow_definition,
    role=workflow_execution_role
)


# ## Review the Amazon States Language code for your workflow
# 
# The following renders the JSON of the [Amazon States Language](https://docs.aws.amazon.com/step-functions/latest/dg/concepts-amazon-states-language.html) definition of the workflow you created. 

# In[13]:


print(workflow.definition.to_json(pretty=True))


# ## Review a visualization for your workflow
# 
# The following cell generates a graphical representation of your workflow.

# In[14]:


workflow.render_graph(portrait=False)


# ## Create the workflow on AWS Step Functions
# 
# Create the workflow in AWS Step Functions with [create](https://aws-step-functions-data-science-sdk.readthedocs.io/en/latest/workflow.html#stepfunctions.workflow.Workflow.create).

# In[15]:


workflow.create()


# ## Execute the workflow
# 
# Run the workflow with [execute](https://aws-step-functions-data-science-sdk.readthedocs.io/en/latest/workflow.html#stepfunctions.workflow.Workflow.execute). Since `IsHelloWorldExample` is set to `True`, your execution should follow the happy path. 

# In[ ]:


execution = workflow.execute(inputs={
        "IsHelloWorldExample": True
})


# ## Review the execution progress
# 
# Render workflow progress with the [render_progress](https://aws-step-functions-data-science-sdk.readthedocs.io/en/latest/workflow.html#stepfunctions.workflow.Execution.render_progress).
# 
# This generates a snapshot of the current state of your workflow as it executes. This is a static image. Run the cell again to check progress. 

# In[ ]:


execution.render_progress()


# ## Review the execution history
# 
# Use [list_events](https://aws-step-functions-data-science-sdk.readthedocs.io/en/latest/workflow.html#stepfunctions.workflow.Execution.list_events) to list all events in the workflow execution.

# In[ ]:


execution.list_events(html=True)


# In[ ]:


get_ipython().system('jupyter nbconvert hello_world_workflow.ipynb --to ')


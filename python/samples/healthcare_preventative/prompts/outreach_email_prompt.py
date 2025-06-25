OUTREACH_EMAIL_PROMPT_TEMPLATE = """Taking into consideration the patient information in {patient} and the criteria in {arguments_criteria}, write an email to the patient named {first_name} {last_name} to arrange a screening. The email should be written in a friendly and professional tone. The email must be no more than 200 words. The email must include the following information: 
1. The name of the screening required: {user_proposal}. 
2. To contact the doctor's office by email or phone to schedule a follow-up appointment. 

Here are other important instructions for the email: 
- Do not provide details about medical history that are not relevant to the screening. 
- Do not provide the reasoning for the screening. 
- Always end the email with 'Best Regards, {name} {phone} {email}' 
- Do not include any disclaimers in the email."""

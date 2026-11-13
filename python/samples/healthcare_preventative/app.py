# Some of the code in this file was generated using AI with GitHub CoPilot, and modified by the author.
# The code is a simulation of a healthcare system that uses AI agents to manage patient outreach
# Author: Benjamin Consolvo
# Originally created in 2025
# Heavily modified from original code by Mick Lynch:
# https://medium.com/@micklynch_6905/hospitalgpt-managing-a-patient-population-with-autogen-powered-by-gpt-4-mixtral-8x7b-ef9f54f275f1
# https://github.com/micklynch/hospitalgpt

import streamlit as st
import pandas as pd
import asyncio
import io
import contextlib
import os
from pathlib import Path
from intelpreventativehealthcare import (
    target_patients_outreach,
    find_patients,
    write_outreach_emails,
    get_configs,
)
# Import the prompt templates
from intelpreventativehealthcare import (
    USER_PROXY_PROMPT,
    EPIDEMIOLOGIST_PROMPT,
    DOCTOR_CRITIC_PROMPT,
    OUTREACH_EMAIL_PROMPT_TEMPLATE,
)
from openai import OpenAI
import streamlit.components.v1 as components  # Add this import for custom HTML

# Streamlit app configuration
st.set_page_config(page_title="Preventative Healthcare Outreach", layout="wide")

# Title at the top of the app
st.title("Cloud Native Agentic Workflows in Healthcare")
st.markdown("""
    Welcome to your preventative healthcare outreach agentic system, built using the open-source framework [AutoGen](https://github.com/microsoft/autogen). 
    
    To improve patient health outcomes, healthcare providers are looking for ways to reach out to patients who may be eligible for preventative screenings. This system is designed to help you automate the process of identifying patients who meet specific screening criteria and generating personalized emails to encourage them to schedule their screenings.
    
    The user provides a very broad screening criteria, and then the system uses AI agents to generate patient-specific criteria, filter patients from a given database, and ultimately write outreach emails to suggest to patients that they schedule a screening. To get the agents working, you can use the sidebar on the left of the UI to:
    1. Customize the prompts for the agents. They use natural language understanding to execute on a workflow. You can use the default ones to get started, and modify to your more specific needs.
    2. Select default (synthetically generated) patient data, or upload your own CSV file.
    3. Describe a medical screening task.
    4. Click on "Generate Outreach Emails" to create draft emails to patients (.txt files with email drafts).
    """)

# Function to read README.md file
def read_readme():
    """
    Reads the README.md file from the project directory and removes the metadata block if present.

    Returns:
        str: The content of the README.md file without the metadata block, or an error message if the file is not found.
    """
    readme_path = Path(__file__).parent / "README.md"
    
    if readme_path.exists():
        with open(readme_path, 'r') as f:
            readme_content = f.read()
            
            # Remove metadata block (everything between the first pair of "---")
            if readme_content.startswith("---"):
                metadata_end = readme_content.find("---", 3)  # Find the closing "---"
                if metadata_end != -1:
                    readme_content = readme_content[metadata_end + 3:].strip()
            
            return readme_content
    else:
        return "README.md file not found in the project directory."

# Function to embed SVG images directly into the markdown content
def fix_svg_images_in_markdown(markdown_content):
    """
    Processes markdown content to embed SVG images directly into the HTML.

    Args:
        markdown_content (str): The markdown content containing <img> tags with SVG sources.

    Returns:
        str: The modified markdown content with embedded SVG images or error messages for missing images.
    """
    import re
    
    # Find SVG image tags in the markdown content
    svg_pattern = r'<img[^>]*src="([^"]*\.svg)"[^>]*>'
    
    def replace_with_embedded_svg(match):
        img_tag = match.group(0)
        src_match = re.search(r'src="([^"]*)"', img_tag)
        if not src_match:
            return img_tag
            
        src_path = src_match.group(1)
        width_match = re.search(r'width="([^"]*)"', img_tag)
        width = width_match.group(1) if width_match else "100%"
        
        # Construct full path to the image
        img_path = Path(__file__).parent / src_path
        
        if img_path.exists():
            try:
                # Read SVG content directly
                with open(img_path, 'r') as f:
                    svg_content = f.read()
                
                # Create a custom HTML component for the SVG with proper styling
                return f"""<div style="text-align:center; margin:20px 0;">
                    <div style="max-width:{width}px; margin:0 auto;">
                        {svg_content}
                    </div>
                </div>"""
            except Exception as e:
                return f"""<div style="text-align:center; color:red; padding:10px;">
                    Error loading SVG image: {e}
                </div>"""
        else:
            return f"""<div style="text-align:center; color:red; padding:10px;">
                Image not found: {src_path}
            </div>"""
    
    # Replace all SVG image tags with embedded SVG content
    return re.sub(svg_pattern, replace_with_embedded_svg, markdown_content)

# Create tabs
tab1, tab2 = st.tabs(["Healthcare Outreach App", "README"])

# Initialize session state for prompts if not already present
if 'user_proxy_prompt' not in st.session_state:
    st.session_state.user_proxy_prompt = USER_PROXY_PROMPT
if 'epidemiologist_prompt' not in st.session_state:
    st.session_state.epidemiologist_prompt = EPIDEMIOLOGIST_PROMPT
if 'doctor_critic_prompt' not in st.session_state:
    st.session_state.doctor_critic_prompt = DOCTOR_CRITIC_PROMPT
if 'outreach_email_prompt' not in st.session_state:
    st.session_state.outreach_email_prompt = OUTREACH_EMAIL_PROMPT_TEMPLATE

# Main Healthcare App Tab (Tab 1)
with tab1:
    # --- Activity/log screen for agent communication ---
    st.markdown("### Activity Log")
    # Create a container with fixed height and scrollbar for logs
    log_container = st.container()
    with log_container:
        # Use an expander that's open by default to contain the log
        with st.expander("Real-time Log", expanded=True):
            log_placeholder = st.empty()

    # --- Move user inputs, instructions, and CSV column info to sidebar ---
    with st.sidebar:
        # Add a section for customizing prompts at the top of the sidebar
        st.markdown("### Customize Agent Prompts")
        st.caption("The agents use LLMs and natural language understanding (NLU) to organize the tasks they need to accomplish. You can modify the prompts for each agent below; these prompts are given to the agents so that they can work together to produce the final outreach emails for the preventative healthcare task at hand.")
        
        # User Proxy Prompt
        with st.expander("User Proxy Prompt"):
            user_prompt = st.text_area(
                "User Proxy Prompt",
                value=st.session_state.user_proxy_prompt, 
                height=300,
                key="user_proxy_input",
                label_visibility="hidden",
                # Add these style properties to preserve whitespace formatting
                help="",
                placeholder="",
                disabled=False,
                # Use CSS to preserve whitespace formatting
                max_chars=None
            )
            st.session_state.user_proxy_prompt = user_prompt
        
        # Epidemiologist Prompt
        with st.expander("Epidemiologist Prompt"):
            epi_prompt = st.text_area(
                "Epidemiologist Prompt", 
                value=st.session_state.epidemiologist_prompt, 
                height=300,
                key="epidemiologist_input",
                label_visibility="hidden",
                help="",
                placeholder="",
                disabled=False,
                max_chars=None
            )
            st.session_state.epidemiologist_prompt = epi_prompt
        
        # Doctor Critic Prompt
        with st.expander("Doctor Critic Prompt"):
            doc_prompt = st.text_area(
                "Doctor Critic Prompt", 
                value=st.session_state.doctor_critic_prompt, 
                height=300,
                key="doctor_critic_input",
                label_visibility="hidden",
                help="",
                placeholder="",
                disabled=False,
                max_chars=None
            )
            st.session_state.doctor_critic_prompt = doc_prompt
        
        # Outreach Email Prompt Template
        with st.expander("Email Template Prompt"):
            email_prompt = st.text_area(
                "Email Template Prompt", 
                value=st.session_state.outreach_email_prompt, 
                height=300,
                key="email_template_input",
                label_visibility="hidden",
                help="",
                placeholder="",
                disabled=False,
                max_chars=None
            )
            st.session_state.outreach_email_prompt = email_prompt
        
        # Add custom CSS to preserve whitespace in text areas while ensuring content fits
        st.markdown("""
        <style>
        .stTextArea textarea {
            font-family: monospace;
            white-space: pre-wrap !important;  /* Use pre-wrap to preserve whitespace but allow wrapping */
            word-wrap: break-word !important;  /* Ensure words break to next line if needed */
            line-height: 1.4;
            tab-size: 2;                       /* Reduce tab size to save space */
            padding: 8px;
            font-size: 0.9em;                  /* Slightly smaller font to fit more content */
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Reset prompts button
        if st.button("Reset Prompts to Default"):
            st.session_state.user_proxy_prompt = USER_PROXY_PROMPT
            st.session_state.epidemiologist_prompt = EPIDEMIOLOGIST_PROMPT
            st.session_state.doctor_critic_prompt = DOCTOR_CRITIC_PROMPT
            st.session_state.outreach_email_prompt = OUTREACH_EMAIL_PROMPT_TEMPLATE
            st.rerun()
        
        st.markdown("---")
        
        # Now add the "Get started" section after the prompts
        st.header("Patient Data and Screening Task")
    
        st.caption("Required CSV columns: patient_id, First Name, Last Name, Email, Patient diagnosis summary, age, gender, condition")
        
        # Create a container for the default dataset option to control its appearance
        default_dataset_container = st.container()
        
        # Add the file upload option after the default dataset option
        uploaded_file = st.file_uploader("Upload your own CSV file with patient data", type=["csv"])
        
        # If a file is uploaded, show a message and disable the default checkbox
        if uploaded_file is not None:
            # Visual indication that custom data is being used
            st.success("✅ Using your uploaded file")
            
            # Disable the default dataset option with clear visual feedback
            with default_dataset_container:
                st.markdown("""
                <div style="opacity: 0.5; pointer-events: none;">
                    <input type="checkbox" disabled> Use default dataset (data/patients.csv)
                    <div style="font-size: 0.8em; color: #999; font-style: italic;">
                        Disabled because custom file is uploaded
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            # Set use_default to False when a file is uploaded
            use_default = False
        else:
            # No file uploaded, show normal checkbox
            with default_dataset_container:
                use_default = st.checkbox("Use default dataset (data/patients.csv)", value=True)
        
        st.markdown("For more information about medical screening tasks, you can visit the website below.")
        st.link_button("U.S. Preventive Services Task Force","https://www.uspreventiveservicestaskforce.org/uspstf/recommendation-topics/uspstf-a-and-b-recommendations")
        screening_task = st.text_input("Enter the medical screening task (e.g., 'Colonoscopy screening').", "Colonoscopy screening")
        
        # Add contact information section
        st.markdown("---")
        st.subheader("Healthcare Provider Contact Information")
        st.caption("This information will appear in the emails sent to patients")
        
        # Create three columns for contact info fields
        col1, col2, col3 = st.columns(3)
        
        with col1:
            provider_name = st.text_input("Provider Name", "Benjamin Consolvo")
            
        with col2:
            provider_email = st.text_input("Provider Email", "doctor@doctor.com")
            
        with col3:
            provider_phone = st.text_input("Provider Phone", "123-456-7890")
        
        # Validate input fields before enabling the button
        required_fields_empty = (
            screening_task.strip() == "" or
            provider_name.strip() == "" or
            provider_email.strip() == "" or
            provider_phone.strip() == ""
        )
        
        if required_fields_empty:
            st.warning("Please fill in all required fields before proceeding.")
        st.markdown("---")
        # Move the button to the sidebar - disabled if required fields are empty
        generate = st.button("Generate Outreach Emails", disabled=required_fields_empty)

    # Explicitly set environment variable to avoid TTY errors
    os.environ["PYTHONUNBUFFERED"] = "1"

    # Only run the generation logic if we're on the first tab
    if tab1._active and generate:
        # Since the button can only be clicked when all fields are filled,
        # we don't need additional validation here
        
        # Hugging Face secrets
        api_key = st.secrets["OPENAI_API_KEY"]
        base_url = st.secrets["OPENAI_BASE_URL"]

        # --- Initialize log ---
        log_messages = []
        def log(msg):
            """
            Logs messages to the activity log container in the Streamlit UI.

            Args:
                msg (str): The message to be logged.
            """
            log_messages.append(msg)
            # Show all messages in the scrollable container with better contrast
            log_placeholder.markdown(
                f"""
                <div style="height: 400px; overflow-y: auto; border: 1px solid #cccccc; 
                     padding: 15px; border-radius: 5px; background-color: rgba(240, 242, 246, 0.4); 
                     color: inherit; font-family: monospace;">
                    {"<br>".join(log_messages)}
                </div>
                """, 
                unsafe_allow_html=True
            )

        # Capture stdout/stderr during the workflow
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()
        with contextlib.redirect_stdout(stdout_buffer), contextlib.redirect_stderr(stderr_buffer):
            if not screening_task:
                st.error("Please enter a medical screening task.")
            elif not uploaded_file and not use_default:
                st.error("Please upload a CSV file or select the default dataset.")
            else:
                # Load patient data
                if uploaded_file:
                    patients_file = uploaded_file
                else:
                    # Use absolute path for default dataset
                    patients_file = os.path.join(os.path.dirname(__file__), "data/patients.csv")

                try:
                    patients_df = pd.read_csv(patients_file)
                except Exception as e:
                    st.error(f"Error reading the CSV file: {e}")
                    st.stop()

                # Validate required columns
                required_columns = [
                    'patient_id', 'First Name', 'Last Name', 'Email',
                    'Patient diagnosis summary', 'age', 'gender', 'condition'
                ]
                if not all(col in patients_df.columns for col in required_columns):
                    st.error(f"The uploaded CSV file is missing required columns: {required_columns}")
                    st.stop()

                # Load configurations
                llama_filter_dict = {"model": ["meta-llama/Llama-3.3-70B-Instruct"]}
                deepseek_filter_dict = {"model": ["deepseek-ai/DeepSeek-R1-Distill-Llama-70B"]}
                config_list_llama = get_configs("OAI_CONFIG_LIST.json", llama_filter_dict)
                config_list_deepseek = get_configs("OAI_CONFIG_LIST.json", deepseek_filter_dict)

                # Ensure the API key from secrets is used
                for config in config_list_llama:
                    config["api_key"] = api_key
                for config in config_list_deepseek:
                    config["api_key"] = api_key

                # --- Log agent communication ---
                log("🟢 <b>Starting agent workflow...</b>")
                log("🧑‍⚕️ <b>Screening task:</b> " + screening_task)
                log("📄 <b>Loaded patient data:</b> {} records".format(len(patients_df)))

                # Generate criteria for outreach - Pass the custom prompts
                log("🤖 <b>Agent (Llama):</b> Generating outreach criteria...")
                criteria = asyncio.run(target_patients_outreach(
                    screening_task, config_list_llama, config_list_deepseek,
                    log_fn=log if "log_fn" in target_patients_outreach.__code__.co_varnames else None,
                    user_proxy_prompt=st.session_state.user_proxy_prompt,
                    epidemiologist_prompt=st.session_state.epidemiologist_prompt,
                    doctor_critic_prompt=st.session_state.doctor_critic_prompt
                ))
                log("✅ <b>Criteria generated.</b>")

                # Find patients matching criteria
                log("🤖 <b>Agent (Llama):</b> Filtering patients based on criteria...")
                filtered_patients, arguments_criteria = asyncio.run(find_patients(
                    criteria, config_list_llama,
                    log_fn=log if "log_fn" in find_patients.__code__.co_varnames else None,
                    patients_file_path=patients_file  # Use correct parameter name: patients_file_path
                ))
                log("✅ <b>Patients filtered.</b>")

                if filtered_patients.empty:
                    log("⚠️ <b>No patients matched the criteria.</b>")
                    st.warning("No patients matched the criteria.")
                else:
                    # Initialize OpenAI client
                    openai_client = OpenAI(api_key=api_key, base_url=base_url)

                    # Generate outreach emails - Pass the custom email template
                    log("🤖 <b>Agent (Llama):</b> Generating outreach emails...")
                    asyncio.run(write_outreach_emails(
                        filtered_patients,
                        screening_task,
                        arguments_criteria,
                        openai_client,
                        config_list_llama[0]['model'],
                        phone=provider_phone,  # Pass the provider's phone from form
                        email=provider_email,  # Pass the provider's email from form
                        name=provider_name,    # Pass the provider's name from form
                        log_fn=log if "log_fn" in write_outreach_emails.__code__.co_varnames else None,
                        outreach_email_prompt_template=st.session_state.outreach_email_prompt
                    ))
                    
                    # Make sure data directory exists (for Hugging Face Spaces)
                    data_dir = os.path.join(os.path.dirname(__file__), "data")
                    os.makedirs(data_dir, exist_ok=True)
                    
                    # Generate expected email filenames based on filtered patients
                    expected_email_files = []
                    for _, patient in filtered_patients.iterrows():
                        # Construct the expected filename based on patient data
                        firstname = patient['First Name']
                        lastname = patient['Last Name']
                        filename = f"{firstname}_{lastname}_email.txt"
                        if os.path.exists(os.path.join(data_dir, filename)):
                            expected_email_files.append(filename)
                    
                    # Use only the email files for patients in the filtered DataFrame
                    email_files = expected_email_files
                    
                    if email_files:
                        log("✅ <b>Outreach emails generated successfully:</b> {} emails created".format(len(email_files)))
                        st.success(f"{len(email_files)} outreach emails have been generated!")
                        
                        # Create a section for downloads
                        st.markdown("### Download Generated Emails")
                        
                        # Store email content in session state to persist across interactions
                        if 'email_contents' not in st.session_state:
                            st.session_state.email_contents = {}
                            for email_file in email_files:
                                with open(os.path.join(data_dir, email_file), 'r') as f:
                                    st.session_state.email_contents[email_file] = f.read()
                        
                        # Create ZIP file only once and store in session state
                        if 'zip_buffer' not in st.session_state:
                            import zipfile
                            zip_buffer = io.BytesIO()
                            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                                for email_file, content in st.session_state.email_contents.items():
                                    zip_file.writestr(email_file, content)
                            st.session_state.zip_buffer = zip_buffer.getvalue()
                        
                        # Create base64 encoding of zip file
                        import base64
                        b64_zip = base64.b64encode(st.session_state.zip_buffer).decode()
                        
                        # Create HTML for ZIP download - Use components.html instead of st.markdown
                        zip_html = f"""
                        <div style="margin-bottom: 20px;">
                            <a href="data:application/zip;base64,{b64_zip}" 
                               download="patient_emails.zip" 
                               style="text-decoration: none; display: inline-block; padding: 12px 18px; 
                               border: 1px solid #ddd; border-radius: 4px; background-color: #4CAF50; 
                               color: white; font-size: 16px; font-weight: bold; text-align: center;">
                                📦 Download All Emails as ZIP
                            </a>
                        </div>
                        """
                        
                        # Use components.html instead of st.markdown for ZIP download
                        components.html(zip_html, height=70)
                        
                        st.markdown("---")
                        st.markdown("#### Individual Email Downloads")
                        
                        # Generate HTML for individual email downloads
                        individual_html = """
                        <div style="display: flex; flex-wrap: wrap; gap: 8px;">
                        """
                        
                        # Generate download links for all emails
                        for i, email_file in enumerate(email_files):
                            file_content = st.session_state.email_contents.get(email_file, "")
                            # Create a base64 encoded version of the file content
                            b64_content = base64.b64encode(file_content.encode()).decode()
                            
                            # Extract a more complete display name (First + Last name)
                            name_parts = email_file.split('_')[:2]  # Get first and last name parts
                            display_name = " ".join(name_parts)  # Join with space to create "First Last"
                            
                            # Add download link to HTML
                            individual_html += f"""
                            <a href="data:text/plain;base64,{b64_content}" 
                               download="{email_file}" 
                               style="text-decoration: none; display: inline-block; margin: 4px; padding: 8px 12px; 
                               border: 1px solid #ddd; border-radius: 4px; background-color: #f0f2f6; 
                               color: #262730; font-size: 14px; text-align: center; min-width: 120px;">
                                {display_name}
                            </a>
                            """
                        
                        individual_html += """
                        </div>
                        """
                        
                        # Use components.html for individual downloads - estimate height based on number of emails
                        # Increase height calculation to account for potentially longer names
                        components.html(individual_html, height=100 + (len(email_files) // 4) * 60)
                        
                    else:
                        log("⚠️ <b>Email generation process completed but no email files were found.</b>")
                        st.warning("The email generation process completed but no email files were found in the data directory. This might indicate an issue with the email generation or file saving process.")

        # After workflow, append captured output
        std_output = stdout_buffer.getvalue()
        std_error = stderr_buffer.getvalue()
        
        if std_output:
            log_messages.append("<b>Terminal Output:</b>")
            for line in std_output.splitlines():
                if line.strip():  # Skip empty lines
                    log_messages.append(line)
            # Update the log display with all messages using better contrast
            log_placeholder.markdown(
                f"""
                <div style="height: 400px; overflow-y: auto; border: 1px solid #cccccc; 
                     padding: 15px; border-radius: 5px; background-color: rgba(240, 242, 246, 0.4); 
                     color: inherit; font-family: monospace;">
                    {"<br>".join(log_messages)}
                </div>
                """, 
                unsafe_allow_html=True
            )
            
        if std_error:
            log_messages.append("<b style='color:#ff6b6b;'>Terminal Error:</b>")
            for line in std_error.splitlines():
                if line.strip():  # Skip empty lines
                    log_messages.append(f"<span style='color:#ff6b6b;'>{line}</span>")
            # Update the log display with all messages
            log_placeholder.markdown(
                f"""
                <div style="height: 400px; overflow-y: auto; border: 1px solid #cccccc; 
                     padding: 15px; border-radius: 5px; background-color: rgba(240, 242, 246, 0.4);
                     color: inherit; font-family: monospace;">
                    {"<br>".join(log_messages)}
                </div>
                """, 
                unsafe_allow_html=True
            )

# README Tab (Tab 2)
with tab2:
    readme_content = read_readme()
    
    # Process the README content to properly handle SVG images
    readme_with_embedded_svgs = fix_svg_images_in_markdown(readme_content)
    
    # Use unsafe_allow_html=True to render HTML content properly
    st.markdown(readme_with_embedded_svgs, unsafe_allow_html=True)
    
    # Add CSS to ensure SVGs are responsive and display properly
    st.markdown("""
    <style>
    svg {
        max-width: 100%;
        height: auto;
    }
    </style>
    """, unsafe_allow_html=True)

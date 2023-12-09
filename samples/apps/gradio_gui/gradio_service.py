import os
import pickle
import importlib
import base64
import gradio as gr
from void_terminal.themes.theme import adjust_theme, advanced_css, theme_declaration, load_dynamic_theme
from void_terminal.request_llms.bridge_all import predict
from void_terminal.core_functional import get_core_functions
from void_terminal.check_proxy import check_proxy, auto_update, warm_up_modules
from void_terminal.crazy_functions.live_audio.audio_io import RealtimeAudioDistribution
from void_terminal.toolbox import (
    format_io,
    find_free_port,
    on_file_uploaded,
    on_report_generated,
    get_conf,
    ArgsGeneralWrapper,
    load_chat_cookies,
    DummyWith,
)

# Avoid unexpected pollution caused by proxy networks
os.environ["no_proxy"] = "*"


def main(plugins: dict):
    if gr.__version__ not in ["3.32.6"]:
        # this is a special version of gradio, which is not available on pypi.org
        raise ModuleNotFoundError(
            "Use the built-in Gradio for the best experience!"
            + "Please run `pip uninstall gradio` and `pip install gradio-stable-fork>=3.32.6` Command to install built-in Gradio."
        )

    proxies, WEB_PORT, LLM_MODEL, CONCURRENT_COUNT, AUTHENTICATION = get_conf(
        "proxies", "WEB_PORT", "LLM_MODEL", "CONCURRENT_COUNT", "AUTHENTICATION"
    )
    CHATBOT_HEIGHT, LAYOUT, AVAIL_LLM_MODELS, AUTO_CLEAR_TXT = get_conf(
        "CHATBOT_HEIGHT", "LAYOUT", "AVAIL_LLM_MODELS", "AUTO_CLEAR_TXT"
    )
    ENABLE_AUDIO, AUTO_CLEAR_TXT, PATH_LOGGING, AVAIL_THEMES, THEME = get_conf(
        "ENABLE_AUDIO", "AUTO_CLEAR_TXT", "PATH_LOGGING", "AVAIL_THEMES", "THEME"
    )
    DARK_MODE, NUM_CUSTOM_BASIC_BTN, SSL_KEYFILE, SSL_CERTFILE = get_conf(
        "DARK_MODE", "NUM_CUSTOM_BASIC_BTN", "SSL_KEYFILE", "SSL_CERTFILE"
    )

    # If WEB_PORT is -1, then a random port will be selected for WEB
    PORT = find_free_port() if WEB_PORT <= 0 else WEB_PORT

    initial_prompt = "Serve me as a writing and programming assistant."
    title_html = f'<h1 align="center">AutoGen</h1>{theme_declaration}'
    description = ""
    description += "</br></br>Instructions for normal conversation: 1. Enter question; 2. Click Submit"
    description += "</br></br>Instructions for Authgen: 1. Enter your demand; 2. Click Your Autogen plugin in the function plugin area"


    # Inquiry record, Python version recommended 3.9+（The newer the better）
    import logging
    import uuid

    os.makedirs(PATH_LOGGING, exist_ok=True)
    try:
        logging.basicConfig(
            filename=f"{PATH_LOGGING}/chat_secrets.log",
            level=logging.INFO,
            encoding="utf-8",
            format="%(asctime)s %(levelname)-8s %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    except Exception:
        logging.basicConfig(
            filename=f"{PATH_LOGGING}/chat_secrets.log",
            level=logging.INFO,
            format="%(asctime)s %(levelname)-8s %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    # Disable logging output from the 'httpx' logger
    logging.getLogger("httpx").setLevel(logging.WARNING)
    print(
        f"All inquiry records will be automatically saved in the local directory ./{PATH_LOGGING}/chat_secrets.log, Please pay attention to self-privacy protection!"
    )

    # Some common functional modules

    functional = get_core_functions()

    # Advanced function plugins
    # from void_terminal.crazy_functional import get_crazy_functions
    # plugins = get_crazy_functions()
    # for k, v in plugins.items():  plugins[k]['Group'] = "Agent"
    # DEFAULT_FN_GROUPS = get_conf('DEFAULT_FN_GROUPS')
    DEFAULT_FN_GROUPS = ["Agent", "Conversation"]
    all_plugin_groups = list(set([g for _, plugin in plugins.items() for g in plugin["Group"].split("|")]))

    def match_group(tags, groups):
        return any([(g in groups) for g in tags.split("|")])

    # Transformation of markdown text format
    gr.Chatbot.postprocess = format_io

    # Make some adjustments in appearance and color
    set_theme = adjust_theme()

    # Proxy and automatic update
    proxy_info = check_proxy(proxies)

    if LAYOUT == "TOP-DOWN":

        def gr_L1():
            return DummyWith()

        def gr_L2(scale, elem_id):
            return gr.Row()

        CHATBOT_HEIGHT /= 2
    else:

        def gr_L1():
            return gr.Row().style()

        def gr_L2(scale, elem_id):
            return gr.Column(scale=scale, elem_id=elem_id)

    cancel_handles = []
    customize_btns = {}
    predefined_btns = {}
    with gr.Blocks(
        title="GPT Academic - AutoGen Special Edition", theme=set_theme, analytics_enabled=False, css=advanced_css
    ) as demo:
        gr.HTML(title_html)
        secret_css, dark_mode, persistent_cookie = (
            gr.Textbox(visible=False),
            gr.Textbox(DARK_MODE, visible=False),
            gr.Textbox(visible=False),
        )
        cookies = gr.State(load_chat_cookies())
        with gr_L1():
            with gr_L2(scale=2, elem_id="gpt-chat"):
                chatbot = gr.Chatbot(label=f"Current model：{LLM_MODEL}", elem_id="gpt-chatbot")
                if LAYOUT == "TOP-DOWN":
                    chatbot.style(height=CHATBOT_HEIGHT)
                history = gr.State([])
            with gr_L2(scale=1, elem_id="gpt-panel"):
                with gr.Accordion("Input area", open=True, elem_id="input-panel") as area_input_primary:
                    with gr.Row():
                        txt = gr.Textbox(show_label=False, placeholder="Input question here.").style(container=False)
                    with gr.Row():
                        submitBtn = gr.Button("Submit", elem_id="elem_submit", variant="primary")
                    with gr.Row():
                        resetBtn = gr.Button("Reset", elem_id="elem_reset", variant="secondary")
                        resetBtn.style(size="sm")
                        stopBtn = gr.Button("Stop", elem_id="elem_stop", variant="secondary")
                        stopBtn.style(size="sm")
                        clearBtn = gr.Button("Clear", elem_id="elem_clear", variant="secondary", visible=True)
                        clearBtn.style(size="sm")
                    if ENABLE_AUDIO:
                        with gr.Row():
                            audio_mic = gr.Audio(
                                source="microphone", type="numpy", streaming=True, show_label=False
                            ).style(container=False)
                    with gr.Row():
                        status = gr.Markdown(
                            f"Tip: Submit by pressing Enter, Press Shift+Enter to line break。Current model: {LLM_MODEL} \n {proxy_info}",
                            elem_id="state-panel",
                        )
                with gr.Accordion("Basic function area", open=False, elem_id="basic-panel") as area_basic_fn:
                    with gr.Row():
                        for k in range(NUM_CUSTOM_BASIC_BTN):
                            customize_btn = gr.Button(
                                "Custom button" + str(k + 1),
                                visible=False,
                                variant="secondary",
                                info_str="Basic function area: Custom button",
                            )
                            customize_btn.style(size="sm")
                            customize_btns.update({"Custom button" + str(k + 1): customize_btn})
                        for k in functional:
                            if ("Visible" in functional[k]) and (not functional[k]["Visible"]):
                                continue
                            variant = functional[k]["Color"] if "Color" in functional[k] else "secondary"
                            functional[k]["Button"] = gr.Button(
                                k, variant=variant, info_str=f"Basic function area: {k}"
                            )
                            functional[k]["Button"].style(size="sm")
                            predefined_btns.update({k: functional[k]["Button"]})
                with gr.Accordion("Function plugin area", open=True, elem_id="plugin-panel") as area_crazy_fn:
                    with gr.Row():
                        gr.Markdown(
                            "The plugin can read text/path in the input area as parameters（Automatically correct the path when uploading files）"
                        )
                    with gr.Row(elem_id="input-plugin-group"):
                        plugin_group_sel = gr.Dropdown(
                            choices=all_plugin_groups,
                            label="",
                            show_label=False,
                            value=DEFAULT_FN_GROUPS,
                            multiselect=True,
                            interactive=True,
                            elem_classes="normal_mut_select",
                        ).style(container=False)
                    with gr.Row():
                        for k, plugin in plugins.items():
                            if not plugin.get("AsButton", True):
                                continue
                            visible = True if match_group(plugin["Group"], DEFAULT_FN_GROUPS) else False
                            variant = plugins[k]["Color"] if "Color" in plugin else "secondary"
                            info = plugins[k].get("Info", k)
                            plugin["Button"] = plugins[k]["Button"] = gr.Button(
                                k, variant=variant, visible=visible, info_str=f"Function plugin area: {info}"
                            ).style(size="sm")
                    with gr.Row():
                        with gr.Accordion("More function plugins", open=False):
                            dropdown_fn_list = []
                            for k, plugin in plugins.items():
                                if not match_group(plugin["Group"], DEFAULT_FN_GROUPS):
                                    continue
                                if not plugin.get("AsButton", True):
                                    # Exclude plugins that are already buttons
                                    dropdown_fn_list.append(k)
                                elif plugin.get("AdvancedArgs", False):
                                    dropdown_fn_list.append(
                                        k
                                    )  # For plugins that require advanced parameters，Also displayed in the dropdown menu
                            with gr.Row():
                                dropdown = gr.Dropdown(
                                    dropdown_fn_list, value=r"Open plugin list", label="", show_label=False
                                ).style(container=False)
                            with gr.Row():
                                plugin_advanced_arg = gr.Textbox(
                                    show_label=True,
                                    label="Advanced parameter input area",
                                    visible=False,
                                    placeholder="Here is the advanced parameter input area for special function plugins",
                                ).style(container=False)
                            with gr.Row():
                                switchy_bt = gr.Button(
                                    r"Please select from the plugin list first", variant="secondary"
                                ).style(size="sm")
                    with gr.Row():
                        with gr.Accordion(
                            "Click to expand the `file upload area`。Upload local files/compressed packages for function plugin calls。",
                            open=False,
                        ):
                            file_upload = gr.Files(
                                label="Any file, Recommend Uploading Compressed File(zip, tar)",
                                file_count="multiple",
                                elem_id="elem_upload",
                            )

        with gr.Floating(init_x="0%", init_y="0%", visible=True, width=None, drag="forbidden"):
            with gr.Row():
                with gr.Tab("Upload file", elem_id="interact-panel"):
                    gr.Markdown(
                        "Please upload local files/zip packages for `Function Plugin Area` function call。Please note: After uploading the file, the input area will be automatically modified to the corresponding path。"
                    )
                    file_upload_2 = gr.Files(
                        label="Any file, Recommend Uploading Compressed File(zip, tar)", file_count="multiple"
                    )

                with gr.Tab("Change model & Prompt", elem_id="interact-panel"):
                    md_dropdown = gr.Dropdown(
                        AVAIL_LLM_MODELS, value=LLM_MODEL, label="Change LLM model/request source"
                    ).style(container=False)
                    top_p = gr.Slider(
                        minimum=-0,
                        maximum=1.0,
                        value=1.0,
                        step=0.01,
                        interactive=True,
                        label="Top-p (nucleus sampling)",
                    )
                    temperature = gr.Slider(
                        minimum=-0,
                        maximum=2.0,
                        value=1.0,
                        step=0.01,
                        interactive=True,
                        label="Temperature",
                    )
                    max_length_sl = gr.Slider(
                        minimum=256,
                        maximum=1024 * 32,
                        value=4096,
                        step=128,
                        interactive=True,
                        label="Local LLM MaxLength",
                    )
                    system_prompt = gr.Textbox(
                        show_label=True,
                        lines=2,
                        placeholder="System Prompt",
                        label="System prompt",
                        value=initial_prompt,
                    )

                with gr.Tab("Interface appearance", elem_id="interact-panel"):
                    theme_dropdown = gr.Dropdown(AVAIL_THEMES, value=THEME, label="Change UI theme").style(
                        container=False
                    )
                    checkboxes = gr.CheckboxGroup(
                        [
                            "Basic function area",
                            "Function plugin area",
                            "Floating input area",
                            "Input clear key",
                            "Plugin parameter area",
                        ],
                        value=["Basic function area", "Function plugin area"],
                        label="Show/hide function area",
                        elem_id="cbs",
                    ).style(container=False)
                    checkboxes_2 = gr.CheckboxGroup(
                        ["Custom menu"], value=[], label="Show/Hide Custom Menu", elem_id="cbs"
                    ).style(container=False)
                    dark_mode_btn = gr.Button("Switch interface brightness ☀", variant="secondary").style(size="sm")
                    dark_mode_btn.click(
                        None,
                        None,
                        None,
                        _js="""() => {
                            if (document.querySelectorAll('.dark').length) {
                                document.querySelectorAll('.dark').forEach(el => el.classList.remove('dark'));
                            } else {
                                document.querySelector('body').classList.add('dark');
                            }
                        }""",
                    )
                with gr.Tab("Help", elem_id="interact-panel"):
                    gr.Markdown(description)

        with gr.Floating(init_x="20%", init_y="50%", visible=False, width="40%", drag="top") as area_input_secondary:
            with gr.Accordion("Floating input area", open=True, elem_id="input-panel2"):
                with gr.Row() as row:
                    row.style(equal_height=True)
                    with gr.Column(scale=10):
                        txt2 = gr.Textbox(
                            show_label=False, placeholder="Input question here.", lines=8, label="Input area 2"
                        ).style(container=False)
                    with gr.Column(scale=1, min_width=40):
                        submitBtn2 = gr.Button("Submit", variant="primary")
                        submitBtn2.style(size="sm")
                        resetBtn2 = gr.Button("Reset", variant="secondary")
                        resetBtn2.style(size="sm")
                        stopBtn2 = gr.Button("Stop", variant="secondary")
                        stopBtn2.style(size="sm")
                        clearBtn2 = gr.Button("Clear", variant="secondary", visible=True)
                        clearBtn2.style(size="sm")

        def to_cookie_str(d):
            # Pickle the dictionary and encode it as a string
            pickled_dict = pickle.dumps(d)
            cookie_value = base64.b64encode(pickled_dict).decode("utf-8")
            return cookie_value

        def from_cookie_str(c):
            # Decode the base64-encoded string and unpickle it into a dictionary
            pickled_dict = base64.b64decode(c.encode("utf-8"))
            return pickle.loads(pickled_dict)

        with gr.Floating(init_x="20%", init_y="50%", visible=False, width="40%", drag="top") as area_customize:
            with gr.Accordion("Custom menu", open=True, elem_id="edit-panel"):
                with gr.Row() as row:
                    with gr.Column(scale=10):
                        AVAIL_BTN = [btn for btn in customize_btns.keys()] + [k for k in functional]
                        basic_btn_dropdown = gr.Dropdown(
                            AVAIL_BTN,
                            value="Custom button 1",
                            label="Select a button in the Basic Function Area that needs to be customized",
                        ).style(container=False)
                        basic_fn_title = gr.Textbox(
                            show_label=False, placeholder="Enter the new button name", lines=1
                        ).style(container=False)
                        basic_fn_prefix = gr.Textbox(
                            show_label=False, placeholder="Enter a new prompt prefix", lines=4
                        ).style(container=False)
                        basic_fn_suffix = gr.Textbox(
                            show_label=False, placeholder="Enter a new prompt suffix", lines=4
                        ).style(container=False)
                    with gr.Column(scale=1, min_width=70):
                        basic_fn_confirm = gr.Button("Confirm and save", variant="primary")
                        basic_fn_confirm.style(size="sm")
                        basic_fn_load = gr.Button("Load saved", variant="primary")
                        basic_fn_load.style(size="sm")

                        def assign_btn(
                            persistent_cookie_,
                            cookies_,
                            basic_btn_dropdown_,
                            basic_fn_title,
                            basic_fn_prefix,
                            basic_fn_suffix,
                        ):
                            ret = {}
                            customize_fn_overwrite_ = cookies_["customize_fn_overwrite"]
                            customize_fn_overwrite_.update(
                                {
                                    basic_btn_dropdown_: {
                                        "Title": basic_fn_title,
                                        "Prefix": basic_fn_prefix,
                                        "Suffix": basic_fn_suffix,
                                    }
                                }
                            )
                            cookies_.update(customize_fn_overwrite_)
                            if basic_btn_dropdown_ in customize_btns:
                                ret.update(
                                    {customize_btns[basic_btn_dropdown_]: gr.update(visible=True, value=basic_fn_title)}
                                )
                            else:
                                ret.update(
                                    {
                                        predefined_btns[basic_btn_dropdown_]: gr.update(
                                            visible=True, value=basic_fn_title
                                        )
                                    }
                                )
                            ret.update({cookies: cookies_})
                            try:
                                persistent_cookie_ = from_cookie_str(persistent_cookie_)  # persistent cookie to dict
                            except Exception:
                                persistent_cookie_ = {}
                            # dict update new value
                            persistent_cookie_["custom_bnt"] = customize_fn_overwrite_
                            persistent_cookie_ = to_cookie_str(persistent_cookie_)  # persistent cookie to dict
                            # write persistent cookie
                            ret.update({persistent_cookie: persistent_cookie_})
                            return ret

                        def reflesh_btn(persistent_cookie_, cookies_):
                            ret = {}
                            for k in customize_btns:
                                ret.update({customize_btns[k]: gr.update(visible=False, value="")})

                            try:
                                persistent_cookie_ = from_cookie_str(persistent_cookie_)  # persistent cookie to dict
                            except Exception:
                                return ret

                            customize_fn_overwrite_ = persistent_cookie_.get("custom_bnt", {})
                            cookies_["customize_fn_overwrite"] = customize_fn_overwrite_
                            ret.update({cookies: cookies_})

                            for k, v in persistent_cookie_["custom_bnt"].items():
                                if v["Title"] == "":
                                    continue
                                if k in customize_btns:
                                    ret.update({customize_btns[k]: gr.update(visible=True, value=v["Title"])})
                                else:
                                    ret.update({predefined_btns[k]: gr.update(visible=True, value=v["Title"])})
                            return ret

                        basic_fn_load.click(
                            reflesh_btn,
                            [persistent_cookie, cookies],
                            [cookies, *customize_btns.values(), *predefined_btns.values()],
                        )
                        h = basic_fn_confirm.click(
                            assign_btn,
                            [
                                persistent_cookie,
                                cookies,
                                basic_btn_dropdown,
                                basic_fn_title,
                                basic_fn_prefix,
                                basic_fn_suffix,
                            ],
                            [persistent_cookie, cookies, *customize_btns.values(), *predefined_btns.values()],
                        )
                        h.then(
                            None,
                            [persistent_cookie],
                            None,
                            _js="""(persistent_cookie)=>{setCookie("persistent_cookie", persistent_cookie, 5);}""",
                        )  # save persistent cookie

        # Interaction between display switch and function area
        def fn_area_visibility(a):
            ret = {}
            ret.update({area_basic_fn: gr.update(visible=("Basic function area" in a))})
            ret.update({area_crazy_fn: gr.update(visible=("Function plugin area" in a))})
            ret.update({area_input_primary: gr.update(visible=("Floating input area" not in a))})
            ret.update({area_input_secondary: gr.update(visible=("Floating input area" in a))})
            ret.update({clearBtn: gr.update(visible=("Input clear key" in a))})
            ret.update({clearBtn2: gr.update(visible=("Input clear key" in a))})
            ret.update({plugin_advanced_arg: gr.update(visible=("Plugin parameter area" in a))})
            if "Floating input area" in a:
                ret.update({txt: gr.update(value="")})
            return ret

        checkboxes.select(
            fn_area_visibility,
            [checkboxes],
            [
                area_basic_fn,
                area_crazy_fn,
                area_input_primary,
                area_input_secondary,
                txt,
                txt2,
                clearBtn,
                clearBtn2,
                plugin_advanced_arg,
            ],
        )

        # Interaction between display switch and function area
        def fn_area_visibility_2(a):
            ret = {}
            ret.update({area_customize: gr.update(visible=("Custom menu" in a))})
            return ret

        checkboxes_2.select(fn_area_visibility_2, [checkboxes_2], [area_customize])

        # Organize repeated control handle combinations
        input_combo = [
            cookies,
            max_length_sl,
            md_dropdown,
            txt,
            txt2,
            top_p,
            temperature,
            chatbot,
            history,
            system_prompt,
            plugin_advanced_arg,
        ]
        output_combo = [cookies, chatbot, history, status]
        predict_args = dict(fn=ArgsGeneralWrapper(predict), inputs=[*input_combo, gr.State(True)], outputs=output_combo)
        # Submit button, reset button
        cancel_handles.append(txt.submit(**predict_args))
        cancel_handles.append(txt2.submit(**predict_args))
        cancel_handles.append(submitBtn.click(**predict_args))
        cancel_handles.append(submitBtn2.click(**predict_args))
        resetBtn.click(lambda: ([], [], "Reset"), None, [chatbot, history, status])
        resetBtn2.click(lambda: ([], [], "Reset"), None, [chatbot, history, status])
        clearBtn.click(lambda: ("", ""), None, [txt, txt2])
        clearBtn2.click(lambda: ("", ""), None, [txt, txt2])
        if AUTO_CLEAR_TXT:
            submitBtn.click(lambda: ("", ""), None, [txt, txt2])
            submitBtn2.click(lambda: ("", ""), None, [txt, txt2])
            txt.submit(lambda: ("", ""), None, [txt, txt2])
            txt2.submit(lambda: ("", ""), None, [txt, txt2])
        # Registration of callback functions in basic function area
        for k in functional:
            if ("Visible" in functional[k]) and (not functional[k]["Visible"]):
                continue
            click_handle = functional[k]["Button"].click(
                fn=ArgsGeneralWrapper(predict), inputs=[*input_combo, gr.State(True), gr.State(k)], outputs=output_combo
            )
            cancel_handles.append(click_handle)
        for btn in customize_btns.values():
            click_handle = btn.click(
                fn=ArgsGeneralWrapper(predict),
                inputs=[*input_combo, gr.State(True), gr.State(btn.value)],
                outputs=output_combo,
            )
            cancel_handles.append(click_handle)
        # File upload area，Interaction with chatbot after receiving files
        file_upload.upload(
            on_file_uploaded, [file_upload, chatbot, txt, txt2, checkboxes, cookies], [chatbot, txt, txt2, cookies]
        )
        file_upload_2.upload(
            on_file_uploaded, [file_upload_2, chatbot, txt, txt2, checkboxes, cookies], [chatbot, txt, txt2, cookies]
        )
        # Function plugin - fixed button area
        for k in plugins:
            if not plugins[k].get("AsButton", True):
                continue
            click_handle = plugins[k]["Button"].click(
                ArgsGeneralWrapper(plugins[k]["Function"]), [*input_combo], output_combo
            )
            click_handle.then(on_report_generated, [cookies, file_upload, chatbot], [cookies, file_upload, chatbot])
            if AUTO_CLEAR_TXT:
                plugins[k]["Button"].click(lambda: ("", ""), None, [txt, txt2])
            cancel_handles.append(click_handle)

        # Interaction between dropdown menu and dynamic button in function plugin
        def on_dropdown_changed(k):
            variant = plugins[k]["Color"] if "Color" in plugins[k] else "secondary"
            info = plugins[k].get("Info", k)
            ret = {switchy_bt: gr.update(value=k, variant=variant, info_str=f"Function plugin area: {info}")}
            # Whether to call the advanced plugin parameter area
            if plugins[k].get("AdvancedArgs", False):
                ret.update(
                    {
                        plugin_advanced_arg: gr.update(
                            visible=True,
                            label=f"Plugin[{k}]Advanced parameter description for plugin："
                            + plugins[k].get("ArgsReminder", ["No advanced parameter function description provided"]),
                        )
                    }
                )
            else:
                ret.update(
                    {plugin_advanced_arg: gr.update(visible=False, label=f"Plugin[{k}]No advanced parameters needed。")}
                )
            return ret

        dropdown.select(on_dropdown_changed, [dropdown], [switchy_bt, plugin_advanced_arg])

        def on_md_dropdown_changed(k):
            return {chatbot: gr.update(label="Current model：" + k)}

        md_dropdown.select(on_md_dropdown_changed, [md_dropdown], [chatbot])

        def on_theme_dropdown_changed(theme, secret_css):
            adjust_theme, css_part1, _, adjust_dynamic_theme = load_dynamic_theme(theme)
            if adjust_dynamic_theme:
                css_part2 = adjust_dynamic_theme._get_theme_css()
            else:
                css_part2 = adjust_theme()._get_theme_css()
            return css_part2 + css_part1

        theme_handle = theme_dropdown.select(on_theme_dropdown_changed, [theme_dropdown, secret_css], [secret_css])
        theme_handle.then(
            None,
            [secret_css],
            None,
            _js="""(css) => {
                var existingStyles = document.querySelectorAll("style[data-loaded-css]");
                for (var i = 0; i < existingStyles.length; i++) {
                    var style = existingStyles[i];
                    style.parentNode.removeChild(style);
                }
                var styleElement = document.createElement('style');
                styleElement.setAttribute('data-loaded-css', css);
                styleElement.innerHTML = css;
                document.head.appendChild(styleElement);
            }
            """,
        )

        # Registration of callback functions for dynamic buttons
        def route(request: gr.Request, k, *args, **kwargs):
            if k in [r"Open plugin list", r"Please select from the plugin list first"]:
                return
            yield from ArgsGeneralWrapper(plugins[k]["Function"])(request, *args, **kwargs)

        click_handle = switchy_bt.click(route, [switchy_bt, *input_combo], output_combo)
        click_handle.then(on_report_generated, [cookies, file_upload, chatbot], [cookies, file_upload, chatbot])
        cancel_handles.append(click_handle)
        # Callback function registration for the stop button
        stopBtn.click(fn=None, inputs=None, outputs=None, cancels=cancel_handles)
        stopBtn2.click(fn=None, inputs=None, outputs=None, cancels=cancel_handles)
        plugins_as_btn = {name: plugin for name, plugin in plugins.items() if plugin.get("Button", None)}

        def on_group_change(group_list):
            btn_list = []
            fns_list = []
            if not group_list:  # Handling special cases：No plugin group selected
                return [
                    *[plugin["Button"].update(visible=False) for _, plugin in plugins_as_btn.items()],
                    gr.Dropdown.update(choices=[]),
                ]
            for k, plugin in plugins.items():
                if plugin.get("AsButton", True):
                    btn_list.append(
                        plugin["Button"].update(visible=match_group(plugin["Group"], group_list))
                    )  # Refresh button
                    if plugin.get("AdvancedArgs", False):
                        dropdown_fn_list.append(
                            k
                        )  # For plugins that require advanced parameters，Also displayed in the dropdown menu
                elif match_group(plugin["Group"], group_list):
                    fns_list.append(k)  # Refresh the drop-down list
            return [*btn_list, gr.Dropdown.update(choices=fns_list)]

        plugin_group_sel.select(
            fn=on_group_change,
            inputs=[plugin_group_sel],
            outputs=[*[plugin["Button"] for name, plugin in plugins_as_btn.items()], dropdown],
        )
        if ENABLE_AUDIO:
            rad = RealtimeAudioDistribution()

            def deal_audio(audio, cookies):
                rad.feed(cookies["uuid"].hex, audio)

            audio_mic.stream(deal_audio, inputs=[audio_mic, cookies])

        def init_cookie(cookies, chatbot):
            # Assign a unique uuid code to each visiting user.
            cookies.update({"uuid": uuid.uuid4()})
            chatbot.append(
                [
                    "Usage of AutoGen GUI:",
                    "(1) Input your query, examples:\n\n"
                    + "- plot $y=x^2$ with $x \\in (-2,1)$, save the image to res.jpg\n\n"
                    + "- find the solution of $sin(x)=cos(x)$ by ploting the culve within $x > 0$, save the image to res.png\n\n"
                    + "- plot $z=cos(x^2+y^2)$, save the image to wave.jpg\n\n"
                    + "(2) click the small red button `AutoGen ...`.",
                ]
            )
            return cookies, chatbot

        demo.load(init_cookie, inputs=[cookies, chatbot], outputs=[cookies, chatbot])
        darkmode_js = """(dark) => {
            dark = dark == "True";
            if (document.querySelectorAll('.dark').length) {
                if (!dark){
                    document.querySelectorAll('.dark').forEach(el => el.classList.remove('dark'));
                }
            } else {
                if (dark){
                    document.querySelector('body').classList.add('dark');
                }
            }
        }"""
        load_cookie_js = """(persistent_cookie) => {
            return getCookie("persistent_cookie");
        }"""
        demo.load(None, inputs=None, outputs=[persistent_cookie], _js=load_cookie_js)
        # Configure dark theme or light theme
        demo.load(None, inputs=[dark_mode], outputs=None, _js=darkmode_js)
        demo.load(
            None,
            inputs=[gr.Textbox(LAYOUT, visible=False)],
            outputs=None,
            _js="(LAYOUT)=>{GptAcademicJavaScriptInit(LAYOUT);}",
        )

    # In-browser triggering of gradio is not very stable，Roll back code to the original browser open function
    def run_delayed_tasks():
        import threading
        import webbrowser
        import time

        print("If the browser does not open automatically，Please copy and go to the following URL：")
        if DARK_MODE:
            print(f"\tDark theme enabled（Support dynamic theme switching）」: http://localhost:{PORT}")
        else:
            print(f"\tLight theme enabled（Support dynamic theme switching）」: http://localhost:{PORT}")

        # def auto_updates(): time.sleep(0); auto_update()
        def open_browser():
            time.sleep(2)
            webbrowser.open_new_tab(f"http://localhost:{PORT}")

        def warm_up_mods():
            time.sleep(4)
            warm_up_modules()

        # threading.Thread(target=auto_updates, name="self-upgrade", daemon=True).start() # Check for automatic updates
        threading.Thread(target=open_browser, name="open-browser", daemon=True).start()  # Open browser page
        threading.Thread(target=warm_up_mods, name="warm-up", daemon=True).start()  # Preheat the tiktoken module

    run_delayed_tasks()
    demo.queue(concurrency_count=CONCURRENT_COUNT).launch(
        quiet=True,
        server_name="0.0.0.0",
        ssl_keyfile=None if SSL_KEYFILE == "" else SSL_KEYFILE,
        ssl_certfile=None if SSL_CERTFILE == "" else SSL_CERTFILE,
        ssl_verify=False,
        server_port=PORT,
        favicon_path=os.path.join(importlib.import_module("void_terminal").__path__[0], "docs/logo.png"),
        auth=AUTHENTICATION if len(AUTHENTICATION) != 0 else None,
        blocked_paths=["config.py", "config_private.py", "docker-compose.yml", "Dockerfile"],
    )


if __name__ == "__main__":
    main()

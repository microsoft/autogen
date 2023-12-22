import {
  IAgentConfig,
  IAgentFlowSpec,
  IFlowConfig,
  ILLMConfig,
  IModelConfig,
  IStatus,
} from "./types";

export const getServerUrl = () => {
  return process.env.GATSBY_API_URL || "/api";
};

export function setCookie(name: string, value: any, days: number) {
  let expires = "";
  if (days) {
    const date = new Date();
    date.setTime(date.getTime() + days * 24 * 60 * 60 * 1000);
    expires = "; expires=" + date.toUTCString();
  }
  document.cookie = name + "=" + (value || "") + expires + "; path=/";
}

export function getCookie(name: string) {
  const nameEQ = name + "=";
  const ca = document.cookie.split(";");
  for (let i = 0; i < ca.length; i++) {
    let c = ca[i];
    while (c.charAt(0) == " ") c = c.substring(1, c.length);
    if (c.indexOf(nameEQ) == 0) return c.substring(nameEQ.length, c.length);
  }
  return null;
}
export function setLocalStorage(
  name: string,
  value: any,
  stringify: boolean = true
) {
  if (stringify) {
    localStorage.setItem(name, JSON.stringify(value));
  } else {
    localStorage.setItem(name, value);
  }
}

export function getLocalStorage(name: string, stringify: boolean = true): any {
  if (typeof window !== "undefined") {
    const value = localStorage.getItem(name);
    try {
      if (stringify) {
        return JSON.parse(value!);
      } else {
        return value;
      }
    } catch (e) {
      return null;
    }
  } else {
    return null;
  }
}

export function fetchJSON(
  url: string | URL,
  payload: any = {},
  onSuccess: (data: any) => void,
  onError: (error: IStatus) => void
) {
  return fetch(url, payload)
    .then(function (response) {
      if (response.status !== 200) {
        console.log(
          "Looks like there was a problem. Status Code: " + response.status,
          response
        );
        response.json().then(function (data) {
          console.log("Error data", data);
        });
        onError({
          status: false,
          message:
            "Connection error " + response.status + " " + response.statusText,
        });
        return;
      }
      return response.json().then(function (data) {
        onSuccess(data);
      });
    })
    .catch(function (err) {
      console.log("Fetch Error :-S", err);
      onError({
        status: false,
        message: `There was an error connecting to server. (${err}) `,
      });
    });
}
export const capitalize = (s: string) => {
  if (typeof s !== "string") return "";
  return s.charAt(0).toUpperCase() + s.slice(1);
};

export function eraseCookie(name: string) {
  document.cookie = name + "=; Path=/; Expires=Thu, 01 Jan 1970 00:00:01 GMT;";
}

export function truncateText(text: string, length = 50) {
  if (text.length > length) {
    return text.substring(0, length) + " ...";
  }
  return text;
}

export const getCaretCoordinates = () => {
  let caretX, caretY;
  const selection = window.getSelection();
  if (selection && selection?.rangeCount !== 0) {
    const range = selection.getRangeAt(0).cloneRange();
    range.collapse(false);
    const rect = range.getClientRects()[0];
    if (rect) {
      caretX = rect.left;
      caretY = rect.top;
    }
  }
  return { caretX, caretY };
};

export const getPrefixSuffix = (container: any) => {
  let prefix = "";
  let suffix = "";
  if (window.getSelection) {
    const sel = window.getSelection();
    if (sel && sel.rangeCount > 0) {
      let range = sel.getRangeAt(0).cloneRange();
      range.collapse(true);
      range.setStart(container!, 0);
      prefix = range.toString();

      range = sel.getRangeAt(0).cloneRange();
      range.collapse(true);
      range.setEnd(container, container.childNodes.length);

      suffix = range.toString();
      console.log("prefix", prefix);
      console.log("suffix", suffix);
    }
  }
  return { prefix, suffix };
};

export const uid = () => {
  return Date.now().toString(36) + Math.random().toString(36).substr(2);
};

export const setCaretToEnd = (element: HTMLElement) => {
  const range = document.createRange();
  const selection = window.getSelection();
  range.selectNodeContents(element);
  range.collapse(false);
  selection?.removeAllRanges();
  selection?.addRange(range);
  element.focus();
};

// return a color between a start and end color using a percentage
export const ColorTween = (
  startColor: string,
  endColor: string,
  percent: number
) => {
  // example startColor = "#ff0000" endColor = "#0000ff" percent = 0.5
  const start = {
    r: parseInt(startColor.substring(1, 3), 16),
    g: parseInt(startColor.substring(3, 5), 16),
    b: parseInt(startColor.substring(5, 7), 16),
  };
  const end = {
    r: parseInt(endColor.substring(1, 3), 16),
    g: parseInt(endColor.substring(3, 5), 16),
    b: parseInt(endColor.substring(5, 7), 16),
  };
  const r = Math.floor(start.r + (end.r - start.r) * percent);
  const g = Math.floor(start.g + (end.g - start.g) * percent);
  const b = Math.floor(start.b + (end.b - start.b) * percent);
  return `rgb(${r}, ${g}, ${b})`;
};

export const guid = () => {
  var w = () => {
    return Math.floor((1 + Math.random()) * 0x10000)
      .toString(16)
      .substring(1);
  };
  return `${w()}${w()}-${w()}-${w()}-${w()}-${w()}${w()}${w()}`;
};

/**
 * Converts a number of seconds into a human-readable string representing the duration in days, hours, minutes, and seconds.
 * @param {number} seconds - The number of seconds to convert.
 * @returns {string} A well-formatted duration string.
 */
export const formatDuration = (seconds: number) => {
  const units = [
    { label: " day", seconds: 86400 },
    { label: " hr", seconds: 3600 },
    { label: " min", seconds: 60 },
    { label: " sec", seconds: 1 },
  ];

  let remainingSeconds = seconds;
  const parts = [];

  for (const { label, seconds: unitSeconds } of units) {
    const count = Math.floor(remainingSeconds / unitSeconds);
    if (count > 0) {
      parts.push(count + (count > 1 ? label + "s" : label));
      remainingSeconds -= count * unitSeconds;
    }
  }

  return parts.length > 0 ? parts.join(" ") : "0 sec";
};

export const sampleWorkflowConfig = () => {
  const llm_model_config: IModelConfig[] = [
    {
      model: "gpt-4-1106-preview",
    },
  ];

  const llm_config: ILLMConfig = {
    config_list: llm_model_config,
    temperature: 0.1,
    timeout: 600,
    cache_seed: null,
  };

  const userProxyConfig: IAgentConfig = {
    name: "userproxy",
    human_input_mode: "NEVER",
    max_consecutive_auto_reply: 5,
    system_message: "",
    llm_config: false,
    code_execution_config: {
      work_dir: null,
      use_docker: false,
    },
  };
  const userProxyFlowSpec: IAgentFlowSpec = {
    type: "userproxy",
    config: userProxyConfig,
  };

  const assistantConfig: IAgentConfig = {
    name: "primary_assistant",
    llm_config: llm_config,
    human_input_mode: "NEVER",
    max_consecutive_auto_reply: 8,
    system_message:
      "You are a helpful assistant that can use available functions when needed to solve problems. At each point, do your best to determine if the user's request has been addressed. IF THE REQUEST HAS NOT BEEN ADDRESSED, RESPOND WITH CODE TO ADDRESS IT. IF A FAILURE OCCURRED (e.g., due to a missing library) AND SOME ADDITIONAL CODE WAS WRITTEN (e.g. code to install the library), ENSURE THAT THE ORIGINAL CODE TO ADDRESS THE TASK STILL GETS EXECUTED. If the request HAS been addressed, respond with a summary of the result. The summary must be written as a coherent helpful response to the user request e.g. 'Sure, here is result to your request ' or 'The tallest mountain in Africa is ..' etc.  The summary MUST end with the word TERMINATE. If the user request is  pleasantry or greeting, you should respond with a pleasantry or greeting and TERMINATE.",
  };

  const assistantFlowSpec: IAgentFlowSpec = {
    type: "assistant",
    config: assistantConfig,
  };

  const workFlowConfig: IFlowConfig = {
    name: "Default Agent Workflow",
    description: "Default Agent Workflow",
    sender: userProxyFlowSpec,
    receiver: assistantFlowSpec,
    type: "default",
  };

  return workFlowConfig;
};

export const getModels = () => {
  const models = [
    {
      model: "gpt-4-1106-preview",
    },
    {
      model: "gpt-3.5-turbo-16k",
    },
    {
      model: "TheBloke/zephyr-7B-alpha-AWQ",
      base_url: "http://localhost:8000/v1",
    },
  ];
  return models;
};

export const getSampleSkill = () => {
  const catSkill = `
  # this is a sample skill. Replace with your own skill function
  import numpy as np
  import matplotlib.pyplot as plt
  from matplotlib import font_manager as fm

  def save_cat_ascii_art_to_png(filename='ascii_cat.png'):
      """
      Creates ASCII art of a cat and saves it to a PNG file.

      :param filename: str, the name of the PNG file to save the ASCII art.
      """
      # ASCII art string
      cat_art = [
          "  /\_/\  ",
          " ( o.o ) ",
          " > ^ <  "
      ]

      # Determine shape of output array
      height = len(cat_art)
      width = max(len(line) for line in cat_art)

      # Create a figure and axis to display ASCII art
      fig, ax = plt.subplots(figsize=(width, height))
      ax.axis('off')  # Hide axes

      # Get a monospace font
      prop = fm.FontProperties(family='monospace')

      # Display ASCII art using text
      for y, line in enumerate(cat_art):
          ax.text(0, height-y-1, line, fontproperties=prop, fontsize=12)

      # Adjust layout
      plt.tight_layout()

      # Save figure to file
      plt.savefig(filename, dpi=120, bbox_inches='tight', pad_inches=0.1)
      plt.close(fig)`;
  return catSkill;
};

export const timeAgo = (dateString: string): string => {
  // Parse the date string into a Date object
  const timestamp = new Date(dateString);

  // Check for invalid date
  if (isNaN(timestamp.getTime())) {
    throw new Error("Invalid date string provided.");
  }

  // Get the current time
  const now = new Date();

  // Calculate the difference in milliseconds
  const timeDifference = now.getTime() - timestamp.getTime();

  // Convert time difference to minutes and hours
  const minutesAgo = Math.floor(timeDifference / (1000 * 60));
  const hoursAgo = Math.floor(minutesAgo / 60);

  // Format the date into a readable format e.g. "November 27"
  const options: Intl.DateTimeFormatOptions = { month: "long", day: "numeric" };
  const formattedDate = timestamp.toLocaleDateString(undefined, options);

  // Determine the time difference string
  let timeAgoStr: string;
  if (minutesAgo < 1) {
    timeAgoStr = "just now";
  } else if (minutesAgo < 60) {
    // Less than an hour ago, display minutes
    timeAgoStr = `${minutesAgo} ${minutesAgo === 1 ? "minute" : "minutes"} ago`;
  } else if (hoursAgo < 24) {
    // Less than a day ago, display hours
    timeAgoStr = `${hoursAgo} ${hoursAgo === 1 ? "hour" : "hours"} ago`;
  } else {
    // More than a day ago, display the formatted date
    timeAgoStr = formattedDate;
  }

  // Return the final readable string
  return timeAgoStr;
};

export const examplePrompts = [
  {
    title: "Stock Price",
    prompt:
      "Plot a chart of NVDA and TESLA stock price YTD. Save the result to a file named nvda_tesla.png",
  },
  {
    title: "Sine Wave",
    prompt:
      "Write a python script to plot a sine wave and save it to disc as a png file sine_wave.png",
  },
  {
    title: "Markdown",
    prompt:
      "List out the top 5 rivers in africa and their length and return that as a markdown table. Do not try to write any code, just write the table",
  },
  {
    title: "Paint",
    prompt:
      "paint a picture of a glass of ethiopian coffee, freshly brewed in a tall glass cup, on a table right in front of a lush green forest scenery",
  },
];

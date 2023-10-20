import { orderBy } from "lodash";
import { IContextDocumentItem, IStatus } from "./types";

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

export const postDocument = (
  doc: IContextDocumentItem,
  onSuccess: (data: any) => void,
  onError: (error: IStatus) => void
) => {
  const serverUrl = process.env.GATSBY_API_URL;
  const postDocumentUrl = `${serverUrl}/context/document/add`;
  const payLoad = {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(doc),
  };
  fetchJSON(postDocumentUrl, payLoad, onSuccess, onError);
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
  // exaple startColor = "#ff0000" endColor = "#0000ff" percent = 0.5
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

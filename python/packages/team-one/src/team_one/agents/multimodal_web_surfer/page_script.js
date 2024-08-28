var MultimodalWebSurfer = MultimodalWebSurfer || (function() {
  let nextLabel = 10;

  let roleMapping = {
      "a": "link",
      "area": "link",
      "button": "button",
      "input, type=button": "button",
      "input, type=checkbox": "checkbox",
      "input, type=email": "textbox",
      "input, type=number": "spinbutton",
      "input, type=radio": "radio",
      "input, type=range": "slider",
      "input, type=reset": "button",
      "input, type=search": "searchbox",
      "input, type=submit": "button",
      "input, type=tel": "textbox",
      "input, type=text": "textbox",
      "input, type=url": "textbox",
      "search": "search",
      "select": "combobox",
      "option": "option",
      "textarea": "textbox"
  };

  let getCursor = function(elm) {
      return window.getComputedStyle(elm)["cursor"];
  };

  let getInteractiveElements = function() {

      let results = []
      let roles = ["scrollbar", "searchbox", "slider", "spinbutton", "switch", "tab", "treeitem", "button", "checkbox", "gridcell", "link", "menuitem", "menuitemcheckbox", "menuitemradio", "option", "progressbar", "radio", "textbox", "combobox", "menu", "tree", "treegrid", "grid", "listbox", "radiogroup", "widget"];
      let inertCursors = ["auto", "default", "none", "text", "vertical-text", "not-allowed", "no-drop"];

      // Get the main interactive elements
      let nodeList = document.querySelectorAll("input, select, textarea, button, [href], [onclick], [contenteditable], [tabindex]:not([tabindex='-1'])");
      for (let i=0; i<nodeList.length; i++) { // Copy to something mutable
          results.push(nodeList[i]);
      }

      // Anything not already included that has a suitable role
      nodeList = document.querySelectorAll("[role]");
      for (let i=0; i<nodeList.length; i++) { // Copy to something mutable
          if (results.indexOf(nodeList[i]) == -1) {
              let role = nodeList[i].getAttribute("role");
	      if (roles.indexOf(role) > -1) {
                  results.push(nodeList[i]);
	      }
	  }
      }

      // Any element that changes the cursor to something implying interactivity
      nodeList = document.querySelectorAll("*");
      for (let i=0; i<nodeList.length; i++) {
         let node = nodeList[i];

         // Cursor is default, or does not suggest interactivity
         let cursor = getCursor(node);
         if (inertCursors.indexOf(cursor) >= 0) {
             continue;
         }

         // Move up to the first instance of this cursor change
         parent = node.parentNode;
         while (parent && getCursor(parent) == cursor) {
             node = parent;
	     parent = node.parentNode;
         }

         // Add the node if it is new
         if (results.indexOf(node) == -1) {
             results.push(node);
         }
      }

      return results;
  };

  let labelElements = function(elements) {
      for (let i=0; i<elements.length; i++) {
          if (!elements[i].hasAttribute("__elementId")) {
              elements[i].setAttribute("__elementId", "" + (nextLabel++));
          }
      }
  };

  let isTopmost = function(element, x, y) {
     let hit = document.elementFromPoint(x, y);

     // Hack to handle elements outside the viewport
     if (hit === null) {
         return true; 
     }

     while (hit) {
         if (hit == element) return true;
         hit = hit.parentNode;
     }
     return false;
  };

  let getFocusedElementId = function() {
     let elm = document.activeElement;
     while (elm) {
         if (elm.hasAttribute && elm.hasAttribute("__elementId")) {
	     return elm.getAttribute("__elementId");
	 }
         elm = elm.parentNode;
     }
     return null;
  };

  let trimmedInnerText = function(element) {
      if (!element) {
          return "";
      }
      let text = element.innerText;
      if (!text) {
          return "";
      }
      return text.trim();
  };

  let getApproximateAriaName = function(element) {
      // Check for aria labels
      if (element.hasAttribute("aria-labelledby")) {
          let buffer = "";
	  let ids = element.getAttribute("aria-labelledby").split(" ");
	  for (let i=0; i<ids.length; i++) {
              let label = document.getElementById(ids[i]);
	      if (label) {
	          buffer = buffer + " " + trimmedInnerText(label);
              }
          }
	  return buffer.trim();
      }

      if (element.hasAttribute("aria-label")) {
	  return element.getAttribute("aria-label");
      }

      // Check for labels
      if (element.hasAttribute("id")) {
          let label_id = element.getAttribute("id");
          let label = "";
          let labels = document.querySelectorAll("label[for='" + label_id + "']");
          for (let j=0; j<labels.length; j++) {
              label += labels[j].innerText + " ";
          }
          label = label.trim();
          if (label != "") {
              return label;
          }
      }

      if (element.parentElement && element.parentElement.tagName == "LABEL") {
          return element.parentElement.innerText;
      }

      // Check for alt text or titles
      if (element.hasAttribute("alt")) {
	  return element.getAttribute("alt")
      }

      if (element.hasAttribute("title")) {
	  return element.getAttribute("title")
      }

      return trimmedInnerText(element);
  };

  let getApproximateAriaRole = function(element) {
      let tag = element.tagName.toLowerCase();
      if (tag == "input" && element.hasAttribute("type")) {
          tag = tag + ", type=" + element.getAttribute("type");
      }

      if (element.hasAttribute("role")) {
          return [element.getAttribute("role"), tag];
      }
      else if (tag in roleMapping) {
          return [roleMapping[tag], tag];
      }
      else {
	  return ["", tag];
      }
  };

  let getInteractiveRects = function() {
      labelElements(getInteractiveElements());
      let elements = document.querySelectorAll("[__elementId]");
      let results = {};
      for (let i=0; i<elements.length; i++) {
         let key = elements[i].getAttribute("__elementId");
         let rects = elements[i].getClientRects();
	 let ariaRole = getApproximateAriaRole(elements[i]);
	 let ariaName = getApproximateAriaName(elements[i]);
	 let vScrollable = elements[i].scrollHeight - elements[i].clientHeight >= 1;

	 let record = {
             "tag_name": ariaRole[1],
	     "role": ariaRole[0],
	     "aria-name": ariaName,
	     "v-scrollable": vScrollable,
	     "rects": []
	 };

         for (const rect of rects) {
	     let x = rect.left + rect.width/2;
             let y = rect.top + rect.height/2;
             if (isTopmost(elements[i], x, y)) {
		 record["rects"].push(JSON.parse(JSON.stringify(rect)));
             }
         }

	 if (record["rects"].length > 0) {
             results[key] = record;
         }
      }
      return results;
  };

  let getVisualViewport = function() {
      let vv = window.visualViewport;
      let de = document.documentElement;
      return {
          "height":     vv ? vv.height : 0,
	  "width":      vv ? vv.width : 0,
	  "offsetLeft": vv ? vv.offsetLeft : 0,
	  "offsetTop":  vv ? vv.offsetTop : 0,
	  "pageLeft":   vv ? vv.pageLeft  : 0,
	  "pageTop":    vv ? vv.pageTop : 0,
	  "scale":      vv ? vv.scale : 0,
	  "clientWidth":  de ? de.clientWidth : 0,
	  "clientHeight": de ? de.clientHeight : 0,
	  "scrollWidth":  de ? de.scrollWidth : 0,
	  "scrollHeight": de ? de.scrollHeight : 0
      };
  };

  let _getMetaTags = function() {
      let meta = document.querySelectorAll("meta");
      let results = {};
      for (let i = 0; i<meta.length; i++) {
          let key = null;
          if (meta[i].hasAttribute("name")) {
              key = meta[i].getAttribute("name");
          }
          else if (meta[i].hasAttribute("property")) {
              key = meta[i].getAttribute("property");
          }
          else {
              continue;
          }
          if (meta[i].hasAttribute("content")) {
              results[key] = meta[i].getAttribute("content");
          }
      }
      return results;
  };

  let _getJsonLd = function() {
      let jsonld = [];
      let scripts = document.querySelectorAll('script[type="application/ld+json"]');
      for (let i=0; i<scripts.length; i++) {
          jsonld.push(scripts[i].innerHTML.trim());
      }
      return jsonld;
   };

   // From: https://www.stevefenton.co.uk/blog/2022/12/parse-microdata-with-javascript/
   let _getMicrodata = function() {
      function sanitize(input) {
          return input.replace(/\s/gi, ' ').trim();
      }

      function addValue(information, name, value) {
          if (information[name]) {
              if (typeof information[name] === 'array') {
                  information[name].push(value);
              } else {
                  const arr = [];
                  arr.push(information[name]);
                  arr.push(value);
                  information[name] = arr;
              }
          } else {
              information[name] = value;
          }
      }

      function traverseItem(item, information) {
         const children = item.children;
        
         for (let i = 0; i < children.length; i++) {
             const child = children[i];

             if (child.hasAttribute('itemscope')) {
                 if (child.hasAttribute('itemprop')) {
                     const itemProp = child.getAttribute('itemprop');
                     const itemType = child.getAttribute('itemtype');

                     const childInfo = {
                         itemType: itemType
                     };

                     traverseItem(child, childInfo);

                     itemProp.split(' ').forEach(propName => {
                         addValue(information, propName, childInfo);
                     });
                 }

             } else if (child.hasAttribute('itemprop')) {
                 const itemProp = child.getAttribute('itemprop');
                 itemProp.split(' ').forEach(propName => {
                     if (propName === 'url') {
                         addValue(information, propName, child.href);
                     } else {
                         addValue(information, propName, sanitize(child.getAttribute("content") || child.content || child.textContent || child.src || ""));
                     }
                 });
                 traverseItem(child, information);
             } else {
                 traverseItem(child, information);
             }
         }
      }

      const microdata = [];

      document.querySelectorAll("[itemscope]").forEach(function(elem, i) {
         const itemType = elem.getAttribute('itemtype');
         const information = {
             itemType: itemType
         };
         traverseItem(elem, information);
         microdata.push(information);
      });
    
      return microdata;
   };

   let getPageMetadata = function() {
       let jsonld = _getJsonLd();
       let metaTags = _getMetaTags();
       let microdata = _getMicrodata();
       let results = {}
       if (jsonld.length > 0) {
           try {
               results["jsonld"] = JSON.parse(jsonld);
           } 
	   catch (e) {
               results["jsonld"] = jsonld;
	   }
       }
       if (microdata.length > 0) {
	   results["microdata"] = microdata;
       }
       for (let key in metaTags) {
	   if (metaTags.hasOwnProperty(key)) {
	       results["meta_tags"] = metaTags;
	       break;
           }
       }
       return results;
   };	

   return {
       getInteractiveRects: getInteractiveRects,
       getVisualViewport: getVisualViewport,
       getFocusedElementId: getFocusedElementId,
       getPageMetadata: getPageMetadata,
   };
})();

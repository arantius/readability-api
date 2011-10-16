var gPageEditorEl = null;
var gLastTargetEl = null;
var gTargetEl = null;
var gTargetElHistory = [];

$(document).ready(function() {
  makeEls();
  gPageEditorEl = $('#page');

  $('form.train').submit(function(event) {
    $('form.train input[name="html"]').val(gPageEditorEl.html());
  });
});

$(document).mouseover(function(event) {
  if (!gPageEditorEl) return;
  if (!gPageEditorEl.has(event.target).length) {
    clearBox();
    return;
  }

  gTargetEl = event.target;
  gTargetElHistory = [gTargetEl];
  targetChanged();
});

$(document).keyup(function(event) {
  if (event.ctrlKey) return;
  if (!gTargetEl) return;
  var char = String.fromCharCode(event.keyCode);
  switch (char) {
  case 'I':
    removeSiblings(gTargetEl);
    clearBox();
    break;
  case 'N':
    if (!gTargetElHistory.length) break;
    gTargetEl = gTargetElHistory.shift();
    targetChanged();
    break;
  case 'R':
    removeEl(gTargetEl);
    clearBox();
    break;
  case 'W':
    if (gTargetEl.parentNode.id == 'page') break;
    gTargetElHistory.unshift(gTargetEl);
    gTargetEl = gTargetEl.parentNode;
    targetChanged();
    break;
  }
});

function removeEl(el) {
  if ('#text' == el.nodeName) return;
  el.style.display = 'none';
  el.setAttribute('train', 'remove');
}

function removeSiblings(el) {
  var s = el.nextSibling;
  while (s) {
    removeEl(s);
    s = s.nextSibling;
  }
  s = el.previousSibling;
  while (s) {
    removeEl(s);
    s = s.previousSibling;
  }
  if (el.parentNode && 'page' != el.parentNode.id) {
    removeSiblings(el.parentNode);
  }
}

function targetChanged() {
  if (gLastTargetEl) {
    gLastTargetEl.style.outline = '';
  }
  gLastTargetEl = gTargetEl;

  showBoxAndLabel(gTargetEl, makeElementLabelString(gTargetEl));
}

//\\ // \\ // \\ // \\ // \\ // \\ // \\ // \\ // \\ // \\ // \\ // \\ // \\ //

var gBorderEls;
var gKeyboxElem;
var gLabelDrawnHigh;
var gLabelEl;

function clearBox() {
  gTargetEl = null;
  gTargetElHistory = [];
  if (gBorderEls != null) {
    for (var i=0; i<4; i++) {
      gBorderEls[i].style.display = "none";
    }
    gLabelEl.style.display = "none";
  }
};

function getPos(elem) {
  var pos = {};
  var originalElement = elem;
  var leftX = 0;
  var leftY = 0;
  if (elem.offsetParent) {
    while (elem.offsetParent) {
      leftX += elem.offsetLeft;
      leftY += elem.offsetTop;
      if (elem != originalElement
          && elem != document.body
          && elem != document.documentElement) {
        leftX -= elem.scrollLeft;
        leftY -= elem.scrollTop;
      }
      elem = elem.offsetParent;
    }
  } else if (elem.x) {
    leftX += elem.x;
    leftY += elem.y;
  }
  pos.x = leftX;
  pos.y = leftY;
  return pos;
}

function getWindowDimensions() {
  var out = {};

  if (window.pageXOffset) {
    out.scrollX = window.pageXOffset;
    out.scrollY = window.pageYOffset;
  } else if (document.documentElement) {
    out.scrollX = document.body.scrollLeft +
        document.documentElement.scrollLeft;
    out.scrollY = document.body.scrollTop +
        document.documentElement.scrollTop;
  } else if (document.body.scrollLeft >= 0) {
    out.scrollX = document.body.scrollLeft;
    out.scrollY = document.body.scrollTop;
  }

  if (document.compatMode == "BackCompat") {
    out.width = document.body.clientWidth;
    out.height = document.body.clientHeight;
  } else {
    out.width = document.documentElement.clientWidth;
    out.height = document.documentElement.clientHeight;
  }

  return out;
}

function makeElementLabelString(elem) {
  var s = "<b style='color:#000'>" + elem.tagName.toLowerCase() + "</b>";
  if (elem.id != '') s += ", id: " + elem.id;
  if (elem.className != '') s += ", class: " + elem.className;
  return s;
}

function makeEls() {
  gBorderEls = [];
  var d, i, s;

  for(i=0; i<4; i++) {
    d = document.createElement("DIV");
    s = d.style;
    s.display = "none";
    s.overflow = "hidden";
    s.position = "absolute";
    s.height = "2px";
    s.width = "2px";
    s.top = "20px";
    s.left = "20px";
    s.zIndex = "5000";
    d.isAardvark = true; // mark as ours
    gBorderEls[i] = d;
    document.body.appendChild(d);
  }
  var be = gBorderEls;
  be[0].style.borderTopWidth = "2px";
  be[0].style.borderTopColor = "#f00";
  be[0].style.borderTopStyle = "solid";
  be[1].style.borderBottomWidth = "2px";
  be[1].style.borderBottomColor = "#f00";
  be[1].style.borderBottomStyle = "solid";
  be[2].style.borderLeftWidth = "2px";
  be[2].style.borderLeftColor = "#f00";
  be[2].style.borderLeftStyle = "solid";
  be[3].style.borderRightWidth = "2px";
  be[3].style.borderRightColor = "#f00";
  be[3].style.borderRightStyle = "solid";

  d = document.createElement("DIV");
  setElementStyleDefault(d, "#fff0cc");
  d.isAardvark = true; // mark as ours
  d.isLabel = true; //
  d.style.borderTopWidth = "0";
  d.style.MozBorderRadiusBottomleft = "6px";
  d.style.MozBorderRadiusBottomright = "6px";
  d.style.WebkitBorderBottomLeftRadius = "6px";
  d.style.WebkitBorderBottomRightRadius = "6px";
  d.style.zIndex = "5005";
  d.style.visibility = "hidden";
  document.body.appendChild(d);
  gLabelEl = d;

  d = document.createElement("DIV");
  setElementStyleDefault(d, "#dfd");
  d.isAardvark = true; // mark as ours
  d.isKeybox = true; //
  d.style.backgroundColor = "#cfc";
  d.style.zIndex = "5008";
  document.body.appendChild(d);
  gKeyboxElem = d;
}

function moveElem(o, x, y) {
  o.style.left = x + "px";
  o.style.top = y + "px";
}

function setElementStyleDefault(elem, bgColor) {
  var s = elem.style;
  s.display = "none";
  s.backgroundColor = bgColor;
  s.borderColor = "black";
  s.borderWidth = "1px 2px 2px 1px";
  s.borderStyle = "solid";
  s.fontFamily = "arial";
  s.textAlign = "left";
  s.color = "#000";
  s.fontSize = "12px";
  s.position = "absolute";
  s.paddingTop = "2px";
  s.paddingBottom = "2px";
  s.paddingLeft = "5px";
  s.paddingRight = "5px";
}

function showBoxAndLabel(elem, string) {
  var pos = getPos(elem)
  var dims = getWindowDimensions();
  var y = pos.y;

  moveElem(gBorderEls[0], pos.x, y);
  gBorderEls[0].style.width = elem.offsetWidth + "px";
  gBorderEls[0].style.display = "";

  moveElem(gBorderEls[1], pos.x, y+elem.offsetHeight-2);
  gBorderEls[1].style.width = (elem.offsetWidth + 2)  + "px";
  gBorderEls[1].style.display = "";

  moveElem(gBorderEls[2], pos.x, y);
  gBorderEls[2].style.height = elem.offsetHeight  + "px";
  gBorderEls[2].style.display = "";

  moveElem(gBorderEls[3], pos.x+elem.offsetWidth-2, y);
  gBorderEls[3].style.height = elem.offsetHeight + "px";
  gBorderEls[3].style.display = "";

  y += elem.offsetHeight + 2;

  gLabelEl.innerHTML = string;
  gLabelEl.style.display = '';

  // adjust the label as necessary to make sure it is within screen and
  // the border is pretty
  if ((y + gLabelEl.offsetHeight) >= dims.scrollY + dims.height) {
    gLabelEl.style.borderTopWidth = "1px";
    gLabelEl.style.MozBorderRadiusTopleft = "6px";
    gLabelEl.style.MozBorderRadiusTopright = "6px";
    gLabelEl.style.WebkitBorderTopLeftRadius = "6px";
    gLabelEl.style.WebkitBorderTopRightRadius = "6px";
    gLabelDrawnHigh = true;
    y =(dims.scrollY + dims.height) - gLabelEl.offsetHeight;
  } else if (gLabelEl.offsetWidth > elem.offsetWidth) {
    gLabelEl.style.borderTopWidth = "1px";
    gLabelEl.style.MozBorderRadiusTopright = "6px";
    gLabelEl.style.WebkitBorderTopRightRadius = "6px";
    gLabelDrawnHigh = true;
  } else if (gLabelDrawnHigh) {
    gLabelEl.style.borderTopWidth = "0";
    gLabelEl.style.MozBorderRadiusTopleft = "";
    gLabelEl.style.MozBorderRadiusTopright = "";
    gLabelEl.style.WebkitBorderTopLeftRadius = "";
    gLabelEl.style.WebkitBorderTopRightRadius = "";
    gLabelDrawnHigh = null;
  }
  moveElem(gLabelEl, pos.x+2, y);
  gLabelEl.style.visibility = "visible";
}

//\\ // \\ // \\ // \\ // \\ // \\ // \\ // \\ // \\ // \\ // \\ // \\ // \\ //

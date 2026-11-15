/* Fills the dropdowns from /api/options, then announces every change.
   Other sections (chart, map, probability) listen for "trend:select":

     document.addEventListener("trend:select", e => {
       const { state, variable, depth } = e.detail;
       // e.g. "AL", "soil_moisture", "0-10cm"   (depth is "" when not applicable)
     });
*/
(async function () {
  const stateSel = document.getElementById("state-select");
  const varSel = document.getElementById("variable-select");
  const depthSel = document.getElementById("depth-select");
  const depthField = document.getElementById("depth-field");
  const definition = document.getElementById("variable-definition");
  const status = document.getElementById("controls-status");

  let parameters = [];

  function currentParam() {
    return parameters.find((p) => p.key === varSel.value);
  }

  // The depth dropdown only exists for measurements that have depths.
  function updateDepths() {
    const depths = (currentParam() || {}).depths || [];
    depthSel.innerHTML = "";
    depths.forEach((d) => {
      const opt = document.createElement("option");
      opt.value = d.key;
      opt.textContent = d.label;
      depthSel.appendChild(opt);
    });
    depthField.hidden = depths.length === 0;
  }

  function announce() {
    const param = currentParam();
    definition.textContent = param ? param.definition : "";
    document.dispatchEvent(
      new CustomEvent("trend:select", {
        detail: {
          state: stateSel.value,
          variable: varSel.value,
          depth: depthField.hidden ? "" : depthSel.value,
        },
      })
    );
  }

  function fill(select, items, valueKey, labelKey) {
    select.innerHTML = "";
    items.forEach((item) => {
      const opt = document.createElement("option");
      opt.value = item[valueKey];
      opt.textContent = item[labelKey] + (item.has_data ? "" : " (no data yet)");
      select.appendChild(opt);
    });
    const first = items.find((i) => i.has_data) || items[0];
    select.value = first[valueKey]; // start on something that has data
    select.disabled = false;
  }

  try {
    const res = await fetch("/api/options");
    if (!res.ok) throw new Error("Server returned " + res.status);
    const opts = await res.json();
    parameters = opts.parameters;

    fill(stateSel, opts.states, "code", "name");
    fill(varSel, opts.parameters, "key", "label");
    updateDepths();

    stateSel.addEventListener("change", announce);
    depthSel.addEventListener("change", announce);
    varSel.addEventListener("change", () => { updateDepths(); announce(); });
    announce();
  } catch (err) {
    status.textContent =
      "We couldn't load the choices. Check that the server is running, then refresh the page.";
    status.hidden = false;
  }
})();

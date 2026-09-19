(function () {
  var root = document.getElementById("quiz-root");
  var dataNode = document.getElementById("quiz-data");
  var printBtn = document.getElementById("print-guide");
  if (printBtn) {
    printBtn.addEventListener("click", function () {
      window.print();
    });
  }
  if (!root || !dataNode) return;
  var quiz = JSON.parse(dataNode.textContent);
  var answered = 0;

  quiz.forEach(function (item, index) {
    var fieldset = document.createElement("fieldset");
    var legend = document.createElement("legend");
    legend.textContent = index + 1 + ". " + item.question;
    fieldset.appendChild(legend);
    var explain = document.createElement("p");
    explain.className = "hint";
    explain.hidden = true;
    item.options.forEach(function (option) {
      var label = document.createElement("label");
      label.className = "checkbox";
      var input = document.createElement("input");
      input.type = "radio";
      input.name = item.id;
      input.value = option.id;
      input.addEventListener("change", function () {
        explain.hidden = false;
        var correct = option.id === item.answer;
        explain.textContent = (correct ? "合適的選擇。" : "這不是最安全的做法。") + " " + item.explain;
        answered += 1;
        if (answered >= quiz.length) {
          fetch("/api/learning/completions", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ module: "quiz", version: "demo-1" }),
          });
        }
      });
      label.appendChild(input);
      label.appendChild(document.createTextNode(option.text));
      fieldset.appendChild(label);
    });
    fieldset.appendChild(explain);
    root.appendChild(fieldset);
  });

  fetch("/api/learning/completions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ module: "guide", version: "demo-1" }),
  });
})();

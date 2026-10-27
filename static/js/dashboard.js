document.addEventListener("DOMContentLoaded", () => {
  const dashboard = document.querySelector("#dashboard");

  if (!dashboard) {
    return;
  }

  const transactionsUrl = dashboard.dataset.transactionsUrl;
  const loginUrl = dashboard.dataset.loginUrl;
  const status = document.querySelector("#dashboard-status");
  const transactionsBody = document.querySelector("#transactions-body");
  const emptyState = document.querySelector("#transactions-empty");
  const transactionCount = document.querySelector("#transaction-count");
  const dialog = document.querySelector("#transaction-dialog");
  const form = document.querySelector("#transaction-form");
  const formTitle = document.querySelector("#transaction-dialog-title");
  const formMessage = document.querySelector("#transaction-form-message");
  const saveButton = document.querySelector("#save-transaction");
  let transactions = [];
  let editingTransactionId = null;

  const currencyFormatter = new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  });

  const compactCurrencyFormatter = new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  });

  const formatCurrency = (value) => currencyFormatter.format(Number(value) || 0);

  const formatDate = (value) => {
    const parsedDate = new Date(`${value}T00:00:00`);
    return new Intl.DateTimeFormat("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    }).format(parsedDate);
  };

  const setStatus = (message = "", isError = false) => {
    status.textContent = message;
    status.classList.toggle("is-error", isError);
  };

  const handleApiResponse = async (response) => {
    if (response.status === 401) {
      window.location.assign(loginUrl);
      throw new Error("Your session has expired. Please log in again.");
    }

    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(data.error || "The request could not be completed.");
    }
    return data;
  };

  const calculateTotals = () => {
    const totals = transactions.reduce(
      (summary, transaction) => {
        const amount = Number(transaction.amount) || 0;
        if (transaction.type === "income") {
          summary.income += amount;
        } else if (transaction.type === "expense") {
          summary.expenses += amount;
        }
        return summary;
      },
      { income: 0, expenses: 0 }
    );

    const balance = totals.income - totals.expenses;
    const savingsRate = totals.income > 0 ? (balance / totals.income) * 100 : 0;

    document.querySelector("#current-balance").textContent = formatCurrency(balance);
    document.querySelector("#total-income").textContent = formatCurrency(totals.income);
    document.querySelector("#total-expenses").textContent = formatCurrency(totals.expenses);
    document.querySelector("#savings-rate").textContent = `${savingsRate.toFixed(1)}%`;
  };

  const renderSpendingChart = () => {
    const now = new Date();
    const weeklyExpenses = [0, 0, 0, 0, 0];

    transactions.forEach((transaction) => {
      if (transaction.type !== "expense") {
        return;
      }

      const transactionDate = new Date(`${transaction.date}T00:00:00`);
      if (
        transactionDate.getFullYear() !== now.getFullYear() ||
        transactionDate.getMonth() !== now.getMonth()
      ) {
        return;
      }

      const weekIndex = Math.min(Math.floor((transactionDate.getDate() - 1) / 7), 4);
      weeklyExpenses[weekIndex] += Number(transaction.amount) || 0;
    });

    const highestExpense = Math.max(...weeklyExpenses, 0);
    const bars = document.querySelectorAll("#spending-chart span");

    bars.forEach((bar, index) => {
      const amount = weeklyExpenses[index];
      const height = highestExpense > 0 ? Math.max((amount / highestExpense) * 100, 8) : 4;
      bar.style.height = `${height}%`;
      bar.querySelector("b").textContent = compactCurrencyFormatter.format(amount);
    });
  };

  const createCell = (content, className = "") => {
    const cell = document.createElement("td");
    cell.className = className;
    if (content instanceof Node) {
      cell.append(content);
    } else {
      cell.textContent = content;
    }
    return cell;
  };

  const renderTransactions = () => {
    transactionsBody.replaceChildren();
    emptyState.hidden = transactions.length !== 0;
    transactionCount.textContent = `${transactions.length} ${
      transactions.length === 1 ? "transaction" : "transactions"
    }`;

    transactions.forEach((transaction) => {
      const row = document.createElement("tr");

      const title = document.createElement("div");
      title.className = "transaction-title";
      title.textContent = transaction.title;
      if (transaction.description) {
        const description = document.createElement("small");
        description.textContent = transaction.description;
        title.append(description);
      }

      const type = document.createElement("span");
      type.className = `transaction-type transaction-type--${transaction.type}`;
      type.textContent = transaction.type;

      const actions = document.createElement("div");
      actions.className = "row-actions";

      const editButton = document.createElement("button");
      editButton.className = "row-action";
      editButton.type = "button";
      editButton.dataset.action = "edit";
      editButton.dataset.transactionId = transaction.id;
      editButton.textContent = "Edit";

      const deleteButton = document.createElement("button");
      deleteButton.className = "row-action row-action--delete";
      deleteButton.type = "button";
      deleteButton.dataset.action = "delete";
      deleteButton.dataset.transactionId = transaction.id;
      deleteButton.textContent = "Delete";

      actions.append(editButton, deleteButton);
      const signedAmount = `${transaction.type === "income" ? "+" : "−"}${formatCurrency(
        transaction.amount
      )}`;

      row.append(
        createCell(formatDate(transaction.date)),
        createCell(title),
        createCell(transaction.category),
        createCell(type),
        createCell(signedAmount, transaction.type === "income" ? "positive" : "negative"),
        createCell(actions)
      );
      transactionsBody.append(row);
    });
  };

  const renderDashboard = () => {
    calculateTotals();
    renderSpendingChart();
    renderTransactions();
  };

  const loadTransactions = async () => {
    setStatus("Loading your financial activity...");
    try {
      const response = await fetch(transactionsUrl, {
        headers: { Accept: "application/json" },
      });
      const data = await handleApiResponse(response);
      transactions = data.transactions;
      renderDashboard();
      setStatus("");
    } catch (error) {
      setStatus(error.message, true);
    }
  };

  const setDefaultDate = () => {
    const today = new Date();
    const localDate = new Date(today.getTime() - today.getTimezoneOffset() * 60000);
    form.elements.date.value = localDate.toISOString().split("T")[0];
  };

  const openTransactionForm = (transaction = null) => {
    form.reset();
    formMessage.hidden = true;
    editingTransactionId = transaction ? transaction.id : null;
    formTitle.textContent = transaction ? "Edit Transaction" : "Add Transaction";
    saveButton.textContent = transaction ? "Update Transaction" : "Save Transaction";

    if (transaction) {
      form.elements.title.value = transaction.title;
      form.elements.amount.value = Number(transaction.amount).toFixed(2);
      form.elements.type.value = transaction.type;
      form.elements.category.value = transaction.category;
      form.elements.date.value = transaction.date;
      form.elements.description.value = transaction.description || "";
    } else {
      form.elements.type.value = "expense";
      setDefaultDate();
    }

    if (typeof dialog.showModal === "function") {
      dialog.showModal();
    } else {
      dialog.setAttribute("open", "");
    }
    form.elements.title.focus();
  };

  const closeTransactionForm = () => {
    if (typeof dialog.close === "function") {
      dialog.close();
    } else {
      dialog.removeAttribute("open");
    }
    editingTransactionId = null;
  };

  const saveTransaction = async (event) => {
    event.preventDefault();
    formMessage.hidden = true;
    saveButton.disabled = true;
    saveButton.textContent = editingTransactionId ? "Updating..." : "Saving...";

    const payload = {
      title: form.elements.title.value.trim(),
      amount: form.elements.amount.value,
      type: form.elements.type.value,
      category: form.elements.category.value.trim(),
      date: form.elements.date.value,
      description: form.elements.description.value.trim() || null,
    };

    const requestUrl = editingTransactionId
      ? `${transactionsUrl}/${editingTransactionId}`
      : transactionsUrl;

    try {
      const response = await fetch(requestUrl, {
        method: editingTransactionId ? "PUT" : "POST",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });
      await handleApiResponse(response);
      closeTransactionForm();
      await loadTransactions();
    } catch (error) {
      formMessage.textContent = error.message;
      formMessage.hidden = false;
    } finally {
      saveButton.disabled = false;
      saveButton.textContent = editingTransactionId ? "Update Transaction" : "Save Transaction";
    }
  };

  const deleteTransaction = async (transaction) => {
    const shouldDelete = window.confirm(`Delete “${transaction.title}”? This cannot be undone.`);
    if (!shouldDelete) {
      return;
    }

    setStatus("Deleting transaction...");
    try {
      const response = await fetch(`${transactionsUrl}/${transaction.id}`, {
        method: "DELETE",
        headers: { Accept: "application/json" },
      });
      await handleApiResponse(response);
      await loadTransactions();
    } catch (error) {
      setStatus(error.message, true);
    }
  };

  document.querySelector("#add-transaction-button").addEventListener("click", () => {
    openTransactionForm();
  });

  document.querySelectorAll("[data-open-transaction-form]").forEach((button) => {
    button.addEventListener("click", () => openTransactionForm());
  });

  transactionsBody.addEventListener("click", (event) => {
    const actionButton = event.target.closest("[data-action]");
    if (!actionButton) {
      return;
    }

    const transactionId = Number(actionButton.dataset.transactionId);
    const transaction = transactions.find((item) => item.id === transactionId);
    if (!transaction) {
      return;
    }

    if (actionButton.dataset.action === "edit") {
      openTransactionForm(transaction);
    } else if (actionButton.dataset.action === "delete") {
      deleteTransaction(transaction);
    }
  });

  form.addEventListener("submit", saveTransaction);
  document.querySelector("#close-transaction-dialog").addEventListener("click", closeTransactionForm);
  document.querySelector("#cancel-transaction").addEventListener("click", closeTransactionForm);
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) {
      closeTransactionForm();
    }
  });

  loadTransactions();
});

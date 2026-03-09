/**
 * OpenClaw Skill: Simple Calculator
 *
 * A clean, safe skill that performs basic math operations.
 * No external dependencies, no network access, no file system access.
 */

const SKILL_NAME = "simple-calculator";
const SKILL_VERSION = "1.0.0";

/**
 * Add two numbers together.
 * @param {number} a - First operand
 * @param {number} b - Second operand
 * @returns {number} Sum of a and b
 */
function add(a, b) {
  if (typeof a !== "number" || typeof b !== "number") {
    throw new TypeError("Both arguments must be numbers");
  }
  return a + b;
}

/**
 * Subtract b from a.
 * @param {number} a - First operand
 * @param {number} b - Second operand
 * @returns {number} Difference of a and b
 */
function subtract(a, b) {
  if (typeof a !== "number" || typeof b !== "number") {
    throw new TypeError("Both arguments must be numbers");
  }
  return a - b;
}

/**
 * Multiply two numbers.
 * @param {number} a - First operand
 * @param {number} b - Second operand
 * @returns {number} Product of a and b
 */
function multiply(a, b) {
  if (typeof a !== "number" || typeof b !== "number") {
    throw new TypeError("Both arguments must be numbers");
  }
  return a * b;
}

/**
 * Divide a by b.
 * @param {number} a - Dividend
 * @param {number} b - Divisor
 * @returns {number} Quotient of a divided by b
 */
function divide(a, b) {
  if (typeof a !== "number" || typeof b !== "number") {
    throw new TypeError("Both arguments must be numbers");
  }
  if (b === 0) {
    throw new Error("Division by zero is not allowed");
  }
  return a / b;
}

/**
 * Handle incoming skill requests.
 * @param {object} request - The skill request object
 * @returns {object} The skill response
 */
function handleRequest(request) {
  const { operation, a, b } = request;

  const operations = {
    add: add,
    subtract: subtract,
    multiply: multiply,
    divide: divide,
  };

  if (!operations[operation]) {
    return {
      success: false,
      error: `Unknown operation: ${operation}. Supported: add, subtract, multiply, divide`,
    };
  }

  try {
    const result = operations[operation](a, b);
    return {
      success: true,
      operation: operation,
      a: a,
      b: b,
      result: result,
    };
  } catch (err) {
    return {
      success: false,
      error: err.message,
    };
  }
}

module.exports = { handleRequest, add, subtract, multiply, divide };

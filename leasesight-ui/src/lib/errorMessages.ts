import { toast } from 'sonner';
import { ApiAuthError } from './api';

export function getErrorMessage(error: unknown): string {
  // Handle HTTP status codes
  if (typeof error === 'number') {
    switch (error) {
      case 401:
      case 403:
        return 'Invalid API Key. Please update your settings.';
      case 429:
        return 'Rate limit reached. Retrying automatically...';
      case 500:
      case 502:
      case 503:
      case 504:
        return 'Server Error: Our team has been notified. Please try again shortly.';
      default:
        return `Error: ${error}`;
    }
  }

  // Handle Error objects
  if (error instanceof ApiAuthError) {
    return error.message || 'Invalid API Key. Please update your settings.';
  }

  if (error instanceof Error) {
    // Extract HTTP status from error message if present (e.g., "API error 429: Too Many Requests")
    const statusMatch = error.message.match(/error (\d{3})/);
    if (statusMatch) {
      return getErrorMessage(parseInt(statusMatch[1]));
    }
    return error.message || 'An unexpected error occurred.';
  }

  return 'An unexpected error occurred.';
}

export function showErrorToast(error: unknown, title = 'Error'): void {
  const message = getErrorMessage(error);
  toast.error(title, {
    description: message,
  });
}

export function showSuccessToast(message: string, title = 'Success'): void {
  toast.success(title, {
    description: message,
  });
}

export function showWarningToast(message: string, title = 'Warning'): void {
  toast.warning(title, {
    description: message,
  });
}

export function showInfoToast(message: string, title = 'Info'): void {
  toast.info(title, {
    description: message,
  });
}

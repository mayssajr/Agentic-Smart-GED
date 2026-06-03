import {
  ALLOWED_PARENT_ORIGINS,
  SOURCE_SYSTEM,
} from '../config/runtime'

export const ASSISTANT_MESSAGE_TYPES = {
  READY: 'assistant:ready',
  BOOTSTRAP: 'assistant:bootstrap',
}

const getTargets = () => {
  const targets = []

  if (window.opener && window.opener !== window) {
    targets.push(window.opener)
  }

  if (window.parent && window.parent !== window) {
    targets.push(window.parent)
  }

  return targets
}

export const announceAssistantReady = () => {
  const message = {
    type: ASSISTANT_MESSAGE_TYPES.READY,
    sourceSystem: SOURCE_SYSTEM,
  }

  for (const target of getTargets()) {
    for (const origin of ALLOWED_PARENT_ORIGINS) {
      target.postMessage(message, origin)
    }
  }
}

export const isAllowedParentOrigin = (origin) =>
  ALLOWED_PARENT_ORIGINS.includes(origin)

const message = $input.first().json;

// Extract basic info
const chatId = message.message.chat.id;
const userId = message.message.from.id;
const firstName = message.message.from.first_name;
const userMessage = message.message.text;
const contact = message.message.contact;

// Define available commands
const commands = {
  '/register': '🚗 Set up your product preferences to get automatic matches\n',
  '/edit': '✏️ Update your product preferences or contact information\n', 
  '/unsubscribe': '🔕 Stop receiving product match notifications\n',
  '/help': '❓ Get help on how to use this service'
};

let response = [];

// Handle contact sharing (check this FIRST)
if (contact) {
  const phone = contact.phone_number;
  const contactFirstName = contact.first_name || '';
  const contactLastName = contact.last_name || '';
  const finalName = `${contactFirstName} ${contactLastName}`.trim() || firstName;
  
  response = [{
    chat_id: chatId,
    message: `✅ Perfect! Phone number verified.\n\n• Name: ${finalName}\n• Phone: ${phone}\n\nNow let's set up your product preferences...`,
    step: 'awaiting_product_type',
    user_data: {
      full_name: finalName,
      phone: phone
    },
    keyboard: {
      keyboard: [["🚗 Vehicles", "🏠 Houses & Stands"]],
      resize_keyboard: true,
      one_time_keyboard: true
    },
    buyer_data: {
      chat_id: chatId,
      name: finalName,
      cell_number: phone,
      registration_step: 'awaiting_product_type',
      preferences: {}
    }
  }];
}

// Handle /register command
else if (userMessage === '/register') {
  response = [{
    chat_id: chatId,
    message: `👋 Welcome ${firstName}! Let's get you registered for product matches.\n\nFirst, what's your full name?`,
    step: 'awaiting_name',
    user_data: { first_name: firstName },
    buyer_data: {
      chat_id: chatId,
      registration_step: 'awaiting_name'
    }
  }];
}

// Handle name input (simple logic for now)
else if (userMessage && !userMessage.startsWith('/') && userMessage.length >= 2) {
  const name = userMessage.trim();
  response = [{
    chat_id: chatId,
    message: `✅ Thanks, ${name}! Now please share your phone number:`,
    step: 'awaiting_contact',
    user_data: { full_name: name },
    keyboard: {
      keyboard: [[{ text: "📱 Share Phone Number", request_contact: true }]],
      resize_keyboard: true,
      one_time_keyboard: true
    },
    buyer_data: {
      chat_id: chatId,
      name: name,
      registration_step: 'awaiting_contact'
    }
  }];
}

// Handle other commands
else if (commands[userMessage]) {
  if (userMessage === '/edit') {
    response = [{
      chat_id: chatId,
      message: "✏️ Edit your preferences - feature coming soon!",
      step: 'menu',
      buyer_data: {
        chat_id: chatId,
        registration_step: 'menu'
      }
    }];
  } else if (userMessage === '/unsubscribe') {
    response = [{
      chat_id: chatId,
      message: "🔕 Unsubscribe - feature coming soon!",
      step: 'menu',
      buyer_data: {
        chat_id: chatId,
        registration_step: 'menu'
      }
    }];
  } else if (userMessage === '/help') {
    response = [{
      chat_id: chatId,
      message: `❓ How to use this service:\n\n• Use /register to set up your product preferences\n• You'll get automatic notifications when matching products are listed\n• Use /edit to update your preferences anytime\n• Use /unsubscribe to stop notifications`,
      step: 'menu',
      buyer_data: {
        chat_id: chatId,
        registration_step: 'menu',
      }
    }];
  }
}

// Handle random messages (fallback)
if (response.length === 0) {
  const commandList = Object.entries(commands)
    .map(([cmd, desc]) => `${cmd} - ${desc}`)
    .join('\n');
    
  response = [{
    chat_id: chatId,
    message: `👋 Hello ${firstName}! I'm your product matching assistant.\n\n${commandList}\n\nPlease click a command above to get started.`,
    step: 'menu',
    keyboard: {
      keyboard: [
        ["/register", "/edit"],
        ["/unsubscribe", "/help"]
      ],
      resize_keyboard: true,
      one_time_keyboard: false
    },
    buyer_data: {
      name: firstName || 'Unknown',
      cell_number: contact || 'Not provided',
      chat_id: chatId,
      registration_step: 'awaiting_product_type',
      preferences: {}
    }
  }];
}

return response.map(item => ({
  json: {
    telegram: {
      chat_id: item.chat_id,
      message: item.message,
      keyboard: item.keyboard || null
    },
    buyer: item.buyer_data
  }
}));

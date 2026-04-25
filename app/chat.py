from flask_socketio import emit, join_room, leave_room
from flask import request
from app import socketio
from app.database import User, Conversation, Message
import uuid
from datetime import datetime

visitor_sessions = {}
agent_sessions = {}

EMOJIS = [
    '😀', '😂', '🥰', '😎', '🤔', '👍', '👎', '❤️',
    '🔥', '🎉', '😢', '😡', '🙏', '👋', '✨', '💯'
]

def log_debug(scope, message):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    print(f"[{timestamp}] [{scope}] {message}")

def get_available_agent():
    log_debug("GET_AGENT", f"当前 agent_sessions: {agent_sessions}")
    if agent_sessions:
        for sid, session_data in agent_sessions.items():
            agent_id = session_data.get('agent_id')
            log_debug("GET_AGENT", f"找到可用客服: sid={sid}, agent_id={agent_id}")
            return sid, agent_id
    log_debug("GET_AGENT", "没有找到可用客服")
    return None, None

@socketio.on('visitor_connect')
def handle_visitor_connect(data):
    log_debug("VISITOR", "=" * 50)
    log_debug("VISITOR", "访客连接事件开始")
    log_debug("VISITOR", f"收到的数据: {data}")
    log_debug("VISITOR", f"WebSocket sid: {request.sid}")
    
    visitor_id = data.get('visitor_id') or str(uuid.uuid4())
    visitor_name = data.get('visitor_name', f'访客_{visitor_id[:8]}')
    log_debug("VISITOR", f"visitor_id: {visitor_id}")
    log_debug("VISITOR", f"visitor_name: {visitor_name}")
    
    user = User.get(visitor_id)
    if not user:
        log_debug("VISITOR", "访客不存在，创建新用户")
        user = User.create(visitor_id, visitor_name, 'visitor')
    else:
        log_debug("VISITOR", "访客已存在，更新活跃时间")
        user.update_last_active()
    
    visitor_sessions[request.sid] = {
        'visitor_id': visitor_id,
        'visitor_name': visitor_name,
        'conversation_id': None
    }
    log_debug("VISITOR", f"更新 visitor_sessions: {visitor_sessions}")
    
    conversation = Conversation.get_by_visitor(visitor_id)
    if not conversation:
        log_debug("VISITOR", "没有找到活跃会话，创建新会话")
        conversation = Conversation.create(visitor_id)
    else:
        log_debug("VISITOR", f"找到现有会话: conversation_id={conversation.conversation_id}, status={conversation.status}")
    
    conversation_id = conversation.conversation_id
    visitor_sessions[request.sid]['conversation_id'] = conversation_id
    log_debug("VISITOR", f"访客加入房间: {conversation_id}")
    join_room(conversation_id)
    
    log_debug("VISITOR", "发送 visitor_connected 事件给访客")
    emit('visitor_connected', {
        'visitor_id': visitor_id,
        'conversation_id': conversation_id,
        'status': conversation.status
    })
    
    log_debug("VISITOR", "检查是否有可用客服...")
    agent_sid, agent_id = get_available_agent()
    
    if agent_id and conversation.status == 'waiting':
        log_debug("VISITOR", f"有可用客服，开始分配: agent_id={agent_id}, agent_sid={agent_sid}")
        conversation.assign_agent(agent_id)
        log_debug("VISITOR", f"会话状态已更新为: active, agent_id={agent_id}")
        
        agent_name = agent_sessions.get(agent_sid, {}).get('agent_name', '客服')
        log_debug("VISITOR", f"客服名称: {agent_name}")
        
        if agent_sid:
            log_debug("VISITOR", f"让客服加入房间: {conversation_id}")
            socketio.server.enter_room(agent_sid, conversation_id)
            log_debug("VISITOR", f"发送 new_conversation 事件给客服 sid={agent_sid}")
            socketio.emit('new_conversation', {
                'conversation_id': conversation_id,
                'visitor_id': visitor_id,
                'visitor_name': visitor_name
            }, room=agent_sid)
        else:
            log_debug("VISITOR", "警告: agent_sid 为空，无法让客服加入房间")
        
        log_debug("VISITOR", f"发送 agent_assigned 事件到房间 {conversation_id}")
        log_debug("VISITOR", f"  - agent_id: {agent_id}")
        log_debug("VISITOR", f"  - agent_name: {agent_name}")
        log_debug("VISITOR", f"  - conversation_id: {conversation_id}")
        emit('agent_assigned', {
            'agent_id': agent_id,
            'agent_name': agent_name,
            'conversation_id': conversation_id,
            'visitor_id': visitor_id
        }, room=conversation_id)
    else:
        log_debug("VISITOR", f"没有可用客服或会话不是 waiting 状态")
        log_debug("VISITOR", f"  - agent_id={agent_id}")
        log_debug("VISITOR", f"  - conversation.status={conversation.status}")
    
    if agent_sessions:
        log_debug("VISITOR", f"发送 update_waiting_list 给所有客服，等待数={len(Conversation.get_waiting())}")
        for sid in agent_sessions.keys():
            socketio.emit('update_waiting_list', {
                'count': len(Conversation.get_waiting())
            }, room=sid)
    
    log_debug("VISITOR", "访客连接事件结束")
    log_debug("VISITOR", "=" * 50)

@socketio.on('agent_connect')
def handle_agent_connect(data):
    log_debug("AGENT", "=" * 50)
    log_debug("AGENT", "客服连接事件开始")
    log_debug("AGENT", f"收到的数据: {data}")
    log_debug("AGENT", f"WebSocket sid: {request.sid}")
    
    agent_id = data.get('agent_id') or str(uuid.uuid4())
    agent_name = data.get('agent_name', f'客服_{agent_id[:8]}')
    log_debug("AGENT", f"agent_id: {agent_id}")
    log_debug("AGENT", f"agent_name: {agent_name}")
    
    user = User.get(agent_id)
    if not user:
        log_debug("AGENT", "客服不存在，创建新用户")
        user = User.create(agent_id, agent_name, 'agent')
    else:
        log_debug("AGENT", "客服已存在，更新活跃时间")
        user.update_last_active()
    
    agent_sessions[request.sid] = {
        'agent_id': agent_id,
        'agent_name': agent_name
    }
    log_debug("AGENT", f"更新 agent_sessions: {agent_sessions}")
    
    conversations = Conversation.get_active_for_agent(agent_id)
    log_debug("AGENT", f"客服的活跃会话数: {len(conversations)}")
    
    log_debug("AGENT", "发送 agent_connected 事件给客服")
    emit('agent_connected', {
        'agent_id': agent_id,
        'active_conversations': [
            {
                'conversation_id': c.conversation_id,
                'visitor_id': c.visitor_id,
                'status': c.status
            } for c in conversations
        ]
    })
    
    log_debug("AGENT", "检查是否有等待中的访客...")
    waiting = Conversation.get_waiting()
    log_debug("AGENT", f"等待中的会话数: {len(waiting)}")
    
    if waiting:
        conversation = waiting[0]
        log_debug("AGENT", f"分配等待中的会话: conversation_id={conversation.conversation_id}")
        conversation.assign_agent(agent_id)
        log_debug("AGENT", f"会话状态已更新为: active, agent_id={agent_id}")
        
        log_debug("AGENT", f"客服加入房间: {conversation.conversation_id}")
        join_room(conversation.conversation_id)
        
        log_debug("AGENT", f"发送 agent_assigned 事件到房间 {conversation.conversation_id}")
        emit('agent_assigned', {
            'agent_id': agent_id,
            'agent_name': agent_name,
            'conversation_id': conversation.conversation_id,
            'visitor_id': conversation.visitor_id
        }, room=conversation.conversation_id)
    else:
        log_debug("AGENT", "没有等待中的会话")
    
    log_debug("AGENT", f"发送 update_waiting_list，等待数={len(Conversation.get_waiting())}")
    emit('update_waiting_list', {
        'count': len(Conversation.get_waiting())
    })
    
    log_debug("AGENT", "客服连接事件结束")
    log_debug("AGENT", "=" * 50)

@socketio.on('send_message')
def handle_send_message(data):
    log_debug("MESSAGE", "=" * 50)
    log_debug("MESSAGE", "发送消息事件开始")
    log_debug("MESSAGE", f"收到的数据: {data}")
    log_debug("MESSAGE", f"WebSocket sid: {request.sid}")
    
    conversation_id = data.get('conversation_id')
    content = data.get('content', '')
    message_type = data.get('message_type', 'text')
    file_name = data.get('file_name')
    file_path = data.get('file_path')
    file_size = data.get('file_size')
    
    log_debug("MESSAGE", f"conversation_id: {conversation_id}")
    log_debug("MESSAGE", f"message_type: {message_type}")
    log_debug("MESSAGE", f"content: {content[:50] if content else ''}...")
    
    sender_id = None
    sender_type = None
    
    if request.sid in visitor_sessions:
        visitor_data = visitor_sessions[request.sid]
        sender_id = visitor_data['visitor_id']
        sender_type = 'visitor'
        if not conversation_id:
            conversation_id = visitor_data.get('conversation_id')
        log_debug("MESSAGE", f"发送者是访客: sender_id={sender_id}")
    elif request.sid in agent_sessions:
        agent_data = agent_sessions[request.sid]
        sender_id = agent_data['agent_id']
        sender_type = 'agent'
        log_debug("MESSAGE", f"发送者是客服: sender_id={sender_id}")
    else:
        log_debug("MESSAGE", "警告: 无法识别发送者身份")
        return
    
    if not all([conversation_id, sender_id, content]):
        log_debug("MESSAGE", f"缺少必要参数: conversation_id={conversation_id}, sender_id={sender_id}, content={bool(content)}")
        return
    
    conversation = Conversation.get(conversation_id)
    if not conversation:
        log_debug("MESSAGE", f"会话不存在: conversation_id={conversation_id}")
        return
    
    log_debug("MESSAGE", f"会话信息: visitor_id={conversation.visitor_id}, agent_id={conversation.agent_id}, status={conversation.status}")
    
    message = Message.create(
        conversation_id=conversation_id,
        sender_id=sender_id,
        sender_type=sender_type,
        content=content,
        message_type=message_type,
        file_name=file_name,
        file_path=file_path,
        file_size=file_size
    )
    log_debug("MESSAGE", f"消息已保存到数据库")
    
    log_debug("MESSAGE", f"发送 new_message 事件到房间 {conversation_id}")
    log_debug("MESSAGE", f"  - sender_id: {sender_id}")
    log_debug("MESSAGE", f"  - sender_type: {sender_type}")
    log_debug("MESSAGE", f"  - content: {content[:30] if len(content) > 30 else content}")
    
    emit('new_message', {
        'conversation_id': conversation_id,
        'sender_id': sender_id,
        'sender_type': sender_type,
        'content': content,
        'message_type': message_type,
        'file_name': file_name,
        'file_size': file_size,
        'created_at': message.created_at
    }, room=conversation_id)
    
    log_debug("MESSAGE", "发送消息事件结束")
    log_debug("MESSAGE", "=" * 50)

@socketio.on('get_history')
def handle_get_history(data):
    log_debug("HISTORY", f"获取历史消息: {data}")
    conversation_id = data.get('conversation_id')
    limit = data.get('limit', 100)
    
    if not conversation_id:
        if request.sid in visitor_sessions:
            conversation_id = visitor_sessions[request.sid].get('conversation_id')
            log_debug("HISTORY", f"从访客会话获取 conversation_id: {conversation_id}")
    
    if not conversation_id:
        log_debug("HISTORY", "没有 conversation_id，返回")
        return
    
    messages = Message.get_by_conversation(conversation_id, limit)
    log_debug("HISTORY", f"获取到 {len(messages)} 条历史消息")
    
    emit('history_messages', {
        'conversation_id': conversation_id,
        'messages': [m.to_dict() for m in messages]
    })

@socketio.on('join_conversation')
def handle_join_conversation(data):
    log_debug("JOIN", "=" * 50)
    log_debug("JOIN", "加入会话事件开始")
    log_debug("JOIN", f"收到的数据: {data}")
    log_debug("JOIN", f"WebSocket sid: {request.sid}")
    
    conversation_id = data.get('conversation_id')
    agent_id = None
    
    if request.sid in agent_sessions:
        agent_id = agent_sessions[request.sid]['agent_id']
        log_debug("JOIN", f"客服 agent_id: {agent_id}")
    
    if not conversation_id or not agent_id:
        log_debug("JOIN", f"缺少参数: conversation_id={conversation_id}, agent_id={agent_id}")
        return
    
    conversation = Conversation.get(conversation_id)
    if not conversation:
        log_debug("JOIN", f"会话不存在: conversation_id={conversation_id}")
        return
    
    log_debug("JOIN", f"会话信息: visitor_id={conversation.visitor_id}, agent_id={conversation.agent_id}, status={conversation.status}")
    
    if conversation.status == 'waiting':
        log_debug("JOIN", "会话是 waiting 状态，分配给当前客服")
        conversation.assign_agent(agent_id)
        log_debug("JOIN", f"会话状态已更新为: active, agent_id={agent_id}")
        
        for sid, visitor_data in visitor_sessions.items():
            if visitor_data.get('conversation_id') == conversation_id:
                log_debug("JOIN", f"发送 agent_assigned 事件给访客 sid={sid}")
                socketio.emit('agent_assigned', {
                    'agent_id': agent_id,
                    'agent_name': agent_sessions[request.sid]['agent_name'],
                    'conversation_id': conversation_id,
                    'visitor_id': conversation.visitor_id
                }, room=sid)
                break
    else:
        log_debug("JOIN", f"会话不是 waiting 状态，直接加入")
    
    log_debug("JOIN", f"客服加入房间: {conversation_id}")
    join_room(conversation_id)
    
    messages = Message.get_by_conversation(conversation_id)
    log_debug("JOIN", f"获取到 {len(messages)} 条历史消息")
    
    log_debug("JOIN", f"发送 conversation_joined 事件给客服")
    emit('conversation_joined', {
        'conversation_id': conversation_id,
        'visitor_id': conversation.visitor_id,
        'status': conversation.status,
        'messages': [m.to_dict() for m in messages]
    })
    
    log_debug("JOIN", "加入会话事件结束")
    log_debug("JOIN", "=" * 50)

@socketio.on('leave_conversation')
def handle_leave_conversation(data):
    conversation_id = data.get('conversation_id')
    log_debug("LEAVE", f"离开会话: conversation_id={conversation_id}")
    if conversation_id:
        leave_room(conversation_id)

@socketio.on('disconnect')
def handle_disconnect():
    log_debug("DISCONNECT", "=" * 50)
    log_debug("DISCONNECT", f"断开连接: sid={request.sid}")
    
    if request.sid in visitor_sessions:
        log_debug("DISCONNECT", f"访客断开: {visitor_sessions[request.sid]}")
        del visitor_sessions[request.sid]
    
    if request.sid in agent_sessions:
        log_debug("DISCONNECT", f"客服断开: {agent_sessions[request.sid]}")
        del agent_sessions[request.sid]
        
        for sid in agent_sessions.keys():
            socketio.emit('update_waiting_list', {
                'count': len(Conversation.get_waiting())
            }, room=sid)
    
    log_debug("DISCONNECT", "=" * 50)

log_debug("INIT", "聊天模块加载完成")

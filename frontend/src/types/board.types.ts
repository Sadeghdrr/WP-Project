// TODO: Define DetectiveBoard, BoardItem, BoardNote, BoardConnection interfaces
// Should mirror backend board app models

export interface DetectiveBoard {
  // TODO: id, case, detective, items, connections
}

export interface BoardItem {
  // TODO: id, board, content_type, object_id, position_x, position_y
}

export interface BoardNote {
  // TODO: id, board, title, content
}

export interface BoardConnection {
  // TODO: id, board, from_item, to_item
}
